"""Building a scraper for Northern Ireland"""

import logging
import re
import time
from time import sleep

import requests
import typer
from bs4 import BeautifulSoup
from joblib import Memory
from loguru import logger as loguru_logger
from requests.adapters import HTTPAdapter, Retry

from .northern_ireland_postcodes import NORTHERN_IRELAND_POSTCODES
from .scotland_epc_data_columns import SCOTLAND_EPC_COLUMNS

BASE_URL = "https://find-energy-certificate.service.gov.uk/"
POSTCODE_URL = "https://find-energy-certificate.service.gov.uk/find-a-certificate/search-by-postcode?postcode={}"
ENERGY_CERTIFICATE_URL = "https://find-energy-certificate.service.gov.uk/energy-certificate/{}"
CACHE_DIR = ".cache"
REQUEST_TIMEOUT = 500
REQUEST_SLEEP = 0.5


memory = Memory(CACHE_DIR, verbose=0)


@memory.cache
def requests_cached(url):
    """Wrapper for caching requests."""
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))

    headers = {"User-agent": "Mozilla/5.0"}

    response = s.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    sleep(REQUEST_SLEEP)

    return response


def parse_response(content):
    """Parses the response of calling postcode url with beautiful Soup
    returns a generator of certificate numbers
    """
    content = BeautifulSoup(content, "html.parser")
    links = [link["href"] for link in content.find_all(re.compile("^a"))]
    certificate_urls = [link for link in links if link.startswith("/energy-certificate")]

    if not certificate_urls:
        return None

    return {certificate.split("/")[-1] for certificate in certificate_urls}


def extract_fields(certificate_number, content, fields):  # noqa: PLR0915
    """Extracts requisite information from a particular certificate number"""
    content = BeautifulSoup(content, "html.parser")

    # Certificate Number
    fields.update({"CERTIFICATE_NUMBER": certificate_number})

    # Address
    address = content.find("p", attrs={"class": "epc-address govuk-body"})
    if address:
        address = address.get_text("/").split("/")
        fields.update(
            {
                "ADDRESS1": address[-3],
                "ADDRESS3": address[-2],
                "POSTCODE": re.sub("\n", "", address[-1]).strip(),
            },
        )

    # Validity
    validity = content.find("p", attrs={"class": "govuk-body govuk-!-font-weight-bold"})
    if validity:
        validity = validity.text

    # Property details (Floor Area + Property Type)
    dl = content.find("dl", attrs={"class": "govuk-summary-list"})
    if dl:
        # _ = dl.find_all("dt", attrs={"class": "govuk-summary-list__keys"}, recursive=True)

        values = dl.find_all("dd", attrs={"class": "govuk-summary-list__value"}, recursive=True)
        values = [re.sub("\n", "", i.text).strip() for i in values]

        if len(values) > 1:
            property_type = values[0]
            total_floor_area = values[1]

        else:
            property_type = None
            total_floor_area = values[0]

        fields.update({"TOTAL_FLOOR_AREA": total_floor_area, "PROPERTY_TYPE": property_type})

    # Current + Potential Energy Rating
    energy_rating = content.find_all("text", attrs={"class": "govuk-!-font-weight-bold"}, limit=2)
    if energy_rating:
        current_energy_rating = energy_rating[0].text
        potential_energy_rating = energy_rating[1].text

        fields.update(
            {
                "CURRENT_ENERGY_RATING": current_energy_rating,
                "POTENTIAL_ENERGY_RATING": potential_energy_rating,
            },
        )

    # Summary (Energy Consumption Current)
    summary = content.find("div", attrs={"id": "summary"})
    if summary:
        f = summary.find_all("p", attrs={"class": "govuk-body"})
        text = "".join([i.text for i in f])
        energy_use_kwh_m2 = re.findall("([0-9]+ kilowatt hours per square metre)", text)
        energy_use_kwh_m2 = re.findall("[0-9]+", energy_use_kwh_m2[0])[0]

        fields.update({"ENERGY_CONSUMPTION_CURRENT": energy_use_kwh_m2})

    # Features, Description, and Rating
    tables = content.find("table", attrs={"class": "govuk-table"})
    if tables:
        features = tables.find_all(
            "th",
            attrs={"class": "govuk-table__cell govuk-!-font-weight-regular"},
        )
        features = [feature.text for feature in features]

        description_and_rating = tables.find_all("td", attrs={"class": "govuk-table__cell"})
        description_and_rating = [desc.text for desc in description_and_rating]
        temp_description = description_and_rating[::2]
        temp_rating = description_and_rating[1::2]

        # In some cases features have inconsistent names, thus hardcoding
        description = {
            "Walls": None,
            "Roof": None,
            "Floor": None,
            "Windows": None,
            "Main heating": None,
            "Main heating control": None,
            "Hot water": None,
            "Lighting": None,
            "Air tightness": None,
            "Secondary heating": None,
        }
        rating = {
            "Walls": None,
            "Roof": None,
            "Floor": None,
            "Windows": None,
            "Main heating": None,
            "Main heating control": None,
            "Hot water": None,
            "Lighting": None,
            "Air tightness": None,
            "Secondary heating": None,
        }

        description.update(dict(zip(features, temp_description, strict=False)))
        rating.update(dict(zip(features, temp_rating, strict=False)))

        if "Wall" in features:
            description["Walls"] = description["Wall"]
            rating["Walls"] = rating["Wall"]

        if "Window" in features:
            description["Windows"] = description["Window"]
            rating["Windows"] = rating["Window"]

        fields.update(
            {
                "WALL_DESCRIPTION": description["Walls"],
                "WALL_ENERGY_EFF": rating["Walls"],
                "WINDOWS_DESCRIPTION": description["Windows"],
                "WINDOWS_ENERGY_EFF": rating["Windows"],
                "ROOF_DESCRIPTION": description["Roof"],
                "ROOF_ENERGY_EFF": rating["Roof"],
                "MAINHEAT_DESCRIPTION": description["Main heating"],
                "MAINHEAT_ENERGY_EFF": rating["Main heating"],
                "MAIN_HEATING_CATEGORY": description["Main heating control"],
                "HOTWATER_DESCRIPTION": description["Hot water"],
                "HOT_WATER_ENERGY_EFF": rating["Hot water"],
                "LIGHTING_DESCRIPTION": description["Lighting"],
                "LIGHTING_ENERGY_EFF": rating["Lighting"],
                "FLOOR_DESCRIPTION": description["Floor"],
                "FLOOR_ENERGY_EFF": rating["Floor"],
                "AIR_TIGHTNESS_DESCRIPTION": description["Air tightness"],
                "AIR_TIGHTNESS_ENERGY_EFF": rating["Air tightness"],
                "SECONDHEATING_DESCRIPTION": description["Secondary heating"],
                "SECONDHEATING_ENERGY_EFF": rating["Secondary heating"],
            },
        )

    # Environmental Impact (Current + Potential)
    environmental_impact = content.find("div", attrs={"id": "energy"})
    if environmental_impact:
        env_impact_potential = environmental_impact.find("p").text

        env_impact = re.findall("impact .{1,11}", env_impact_potential)
        env_potential = re.findall("potential .{1,11}", env_impact_potential)

        env_impact = env_impact[0].split(" ")[-1]
        env_potential = env_potential[0].split(" ")[-1].replace(".", "")

        # Carbon emissions
        carbon_emission = environmental_impact.find(
            "dd",
            attrs={"id": "eir-property-produces"},
            recursive=True,
        )
        potential_carbon_emission = environmental_impact.find(
            "dd",
            attrs={"id": "eir-potential-production"},
            recursive=True,
        )
        carbon_emission = carbon_emission.text
        potential_carbon_emission = potential_carbon_emission.text

        fields.update(
            {
                "CO2_EMISSIONS_CURRENT": carbon_emission,
                "CO2_EMISSIONS_POTENTIAL": potential_carbon_emission,
                "ENVIRONMENTAL_IMPACT_CURRENT": env_impact,
                "ENVIRONMENTAL_IMPACT_POTENTIAL": env_potential,
            },
        )

    # Recommendations
    recommendations = content.find(
        "div",
        attrs={"class": "govuk-body printable-area epb-recommended-improvements"},
    )
    if recommendations:
        steps = recommendations.find_all(attrs={"class": "govuk-heading-m"})
        if steps is None:
            steps = recommendations.find_all("p", attrs={"class": "govuk-heading-m"})
        steps = [step.text for step in steps]

        # Summaries
        summary_values = recommendations.find_all(
            "dd",
            attrs={"class": "govuk-summary-list__value"},
            recursive=True,
        )
        summary_values = [x.text for x in summary_values]

        summary = [re.sub("\n", "", x).strip() for x in summary_values]
        saving = summary[::3]
        cost = summary[1::3]
        # There's a bug in EPC website. It displays a potential rating at the top which is different
        # to this one. We have gone with the one at the top of the page, but I think it's wrong.
        potential_rating = summary[2::3]

        fields.update(
            {
                "RECOMMENDATIONS": {
                    "CERTIFICATE_NUMBER": certificate_number,
                    "IMPROVEMENT_DESCR_TEXT": steps,
                    "ENERGY_RATING_AFTER_IMPROVEMENT": potential_rating,
                    "INDICATIVE_COST": cost,
                    "TYPICAL_SAVINGS": saving,
                },
            },
        )

    # Information
    information = content.find("div", attrs={"id": "information"})

    if information:
        information_keys = information.find_all(
            "dt",
            attrs={"class": "govuk-summary-list__key"},
            recursive=True,
        )
        information_values = information.find_all(
            "dd",
            attrs={"class": "govuk-summary-list__value"},
            recursive=True,
        )
        assessment_type = information.find("span", attrs={"class": "govuk-details__summary-text"})
        assessment_type = assessment_type.text.strip().split(" ")[-1]

        information_values = [re.sub("\n", "", i.text).strip() for i in information_values]
        information_keys = [i.text for i in information_keys]

        # Excludes assessment type
        information_keys = information_keys[:-1]
        information_values = information_values[:-1]

        information = dict(zip(information_keys, information_values, strict=False))

        fields.update(
            {
                "TYPE_OF_ASSESSMENT": assessment_type,
                "INSPECTION_DATE": information["Date of assessment"],
                "CREATED_AT": information["Date of assessment"],
            },
        )
    return fields


def main(logger=None):
    """Scraper Runner"""
    if logger == "loguru":
        logger = loguru_logger
    if not logger:
        logger = logging.getLogger("airbyte")

    for postcode in NORTHERN_IRELAND_POSTCODES:
        certificates = []
        source = requests_cached(POSTCODE_URL.format(postcode))
        if source.status_code == 200:
            certificate_numbers = parse_response(source.content)
            if not certificate_numbers:
                time.sleep(0.5)
                continue
            for certificate in set(certificate_numbers):
                response = requests_cached(ENERGY_CERTIFICATE_URL.format(certificate))
                if response.status_code == 200:
                    try:
                        fields = extract_fields(
                            certificate,
                            response.content,
                            fields=SCOTLAND_EPC_COLUMNS,
                        )
                        certificates.append(fields)
                        time.sleep(1)
                    except Exception as e:
                        logger.warning(f"Unable to extract information from {certificate}: {e}")
                        continue
                else:
                    logger.warning(
                        f"Certificate {certificate} returned status code {response.status_code}",
                    )
                    continue
        else:
            logger.warning(f"Postcode {postcode} returned status code {source.status_code}")
            continue

        yield certificates

        time.sleep(2)


if __name__ == "__main__":
    typer.run(main)
