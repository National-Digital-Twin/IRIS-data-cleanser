"""Building a scraper for Northern Ireland"""

import logging
import re
import time
from itertools import islice
from pathlib import Path
from time import sleep

import pandas as pd
import requests
import tqdm
import typer
import yaml
from bs4 import BeautifulSoup
from joblib import Memory
from requests.adapters import HTTPAdapter, Retry
from sqlalchemy import create_engine

BASE_URL = "https://find-energy-certificate.service.gov.uk/"
POSTCODE_URL = "https://find-energy-certificate.service.gov.uk/find-a-certificate/search-by-postcode?postcode={}"
ENERGY_CERTIFICATE_URL = "https://find-energy-certificate.service.gov.uk/energy-certificate/{}"
CACHE_DIR = ".cache"
REQUEST_TIMEOUT = 500
REQUEST_SLEEP = 0.5


memory = Memory(CACHE_DIR, verbose=0)


##DATABASE CONFIG
with open(Path.home() / ".dbt/profiles.yml", encoding="utf-8") as file:
    CONFIG = yaml.safe_load(file)
db_config = CONFIG["c477_data_cleansing"]["outputs"]["dev_postgres"]
db_config = {
    "user": "emmanuel",
    "host": "127.0.0.1",
    "port": "5332",
    "dbname": "postgres",
    "password": "ENTER SOMETHING HERE",  # pragma: allowlist secret
}


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


def write_to_db(df, table="destination", db_config=db_config, exists="replace"):
    """Writes a dataframe to database"""
    conn_string = (
        "postgresql+psycopg2://"
        f"{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}"
        f":{db_config['port']}"
        f"/{db_config['dbname']}"
    )
    engine = create_engine(conn_string, pool_recycle=3600)
    with engine.begin() as connection:
        df.to_sql(
            name=table,
            con=connection,
            index=False,
            if_exists=exists,
            chunksize=1000,
        )

    typer.echo(f"{len(df)} rows uploaded to {table} ✨")


def parse_response(content):
    """Parses the response of calling postcode url with beautiful Soup
    returns a generator of certificate numbers
    """
    content = BeautifulSoup(content, "html.parser")
    links = content.find_all(re.compile("^a"))

    links = [i["href"] for i in links]
    cert_number = [link for link in links if link.startswith("/energy-certificate")]

    del links
    if len(cert_number) == 0:
        return None
    else:
        for i in cert_number:
            yield i.split("/")[-1]


def get_postcodes():
    """Creates a generator of all Northern Ireland postcodes"""

    with open("data/raw/northern_ireland_postcodes.txt") as ins:
        files = tqdm.tqdm(ins.readlines())
        yield from files


def get_scot_columns():
    """Obtains columns present in scotland epc certificates"""
    with open("data/raw/scot_epc_data_columns.txt") as ins:
        columns = ins.readlines()
    return columns


def extract_fields(content, columns=None):  # noqa: PLR0915
    """Extracts requisite information from a particular certificate number"""
    if columns is None:
        columns = []
    fields = {re.sub("\n", "", k): None for k in columns}
    content = BeautifulSoup(content, "html.parser")

    # Address and validity
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

    validity = content.find("p", attrs={"class": "govuk-body govuk-!-font-weight-bold"})
    if validity:
        validity = validity.text

    # Property details
    dl = content.find("dl", attrs={"class": "govuk-summary-list"})
    if dl:
        _ = dl.find_all("dt", attrs={"class": "govuk-summary-list__keys"}, recursive=True)

        values = dl.find_all("dd", attrs={"class": "govuk-summary-list__value"}, recursive=True)
        values = [re.sub("\n", "", i.text).strip() for i in values]

        if len(values) > 1:
            property_type = values[0]
            total_floor_area = values[1]

        else:
            property_type = None
            total_floor_area = values[0]

        fields.update({"TOTAL_FLOOR_AREA": total_floor_area, "PROPERTY_TYPE": property_type})

        del values
        del dl
    # Obtaining current and potential energy rating
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
        del energy_rating

    ##Summaries
    summary = content.find("div", attrs={"id": "summary"})
    if summary:
        f = summary.find_all("p", attrs={"class": "govuk-body"})

        text = "".join([i.text for i in f])
        energy_use_kwh_m2 = re.findall("([0-9]+ kilowatt hours per square metre)", text)
        energy_use_kwh_m2 = re.findall("[0-9]+", energy_use_kwh_m2[0])[0]

        fields.update({"ENERGY_CONSUMPTION_CURRENT": energy_use_kwh_m2})

        del summary

    # Obtaining features, description, and rating from a table
    tables = content.find("table", attrs={"class": "govuk-table"})
    if tables:
        features = tables.find_all(
            "th",
            attrs={"class": "govuk-table__cell govuk-!-font-weight-regular"},
        )
        description_and_rating = tables.find_all("td", attrs={"class": "govuk-table__cell"})

        features = [feature.text for feature in features]
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

        del description_and_rating
        del tables

    # Environmental Potential and Impact
    environmental_impact = content.find("div", attrs={"id": "energy"})
    if environmental_impact:
        env_impact_potential = environmental_impact.find("p").text

        env_impact = re.findall("impact .{1,11}", env_impact_potential)
        env_potential = re.findall("potential .{1,11}", env_impact_potential)

        env_impact = env_impact[0].split(" ")[-1]
        env_potential = env_potential[0].split(" ")[-1]

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

        del environmental_impact

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

        ##Summaries
        summary_values = recommendations.find_all(
            "dd",
            attrs={"class": "govuk-summary-list__value"},
            recursive=True,
        )
        summary_values = [x.text for x in summary_values]
        # potential_rating = re.findall("(\d{1,3}\s*[A-Z]+)", "".join(summary_values))

        summary = [re.sub("\n", "", x).strip() for x in summary_values]

        saving = summary[::3]
        cost = summary[1::3]
        potential_rating = summary[2::3]

        del recommendations
        del summary_values
        fields.update(
            {
                "IMPROVEMENTS": {
                    "IMPROVEMENT_DESCR_TEXT": steps,
                    "ENERGY_RATING_AFTER_IMPROVEMENT": potential_rating,
                    "INDICATIVE_COST": cost,
                    "TYPICAL_SAVINGS": saving,
                },
            },
        )

    ## Information
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

        # excludes assessment type
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
    if logger is None:
        logger = logging.getLogger("airbyte")

    post_codes = get_postcodes()
    scot_columns = get_scot_columns()

    certificates = []
    temp_improvements = []
    unavailable = []
    # unavailable post_codes

    req_count = 0
    for post_code in islice(post_codes, 56495, 57000):
        source = requests_cached(POSTCODE_URL.format(post_code))
        req_count += 1
        # temp-code
        if len(temp_improvements) > 1000:
            temp_improvements = pd.DataFrame(temp_improvements)
            write_to_db(
                temp_improvements,
                table="northern_ireland_recommendations",
                exists="append",
                db_config=db_config,
            )
            temp_improvements = []
        if len(certificates) > 1000:
            certificates = pd.DataFrame(certificates)
            temp_certificates = certificates.drop(columns="IMPROVEMENTS")
            write_to_db(
                temp_certificates,
                table="northern_ireland_epc",
                exists="append",
                db_config=db_config,
            )
            certificates = []
        if len(unavailable) > 1000:
            with open("data/raw/unavailable_certs.txt", "w") as outs:
                outs.writelines(unavailable + ",")
                unavailable = []
        if source.status_code == 200:
            cert_number = parse_response(source.content)
            if cert_number is None:
                continue
            for cert in set(cert_number):
                r = requests_cached(ENERGY_CERTIFICATE_URL.format(cert))
                req_count += 1
                if r.status_code == 200:
                    try:
                        fields = extract_fields(r.content, columns=scot_columns)
                        fields.update({"CERTIFICATE_NUMBER": cert})
                        certificates.append(fields)
                        if fields["IMPROVEMENTS"]:
                            fields["IMPROVEMENTS"].update({"CERTIFICATE_NUMBER": cert})
                            temp_improvements.append(fields["IMPROVEMENTS"])
                        time.sleep(1)
                    except Exception:
                        # logger.warning(f"Unable to extract information from {cert}")
                        print(cert)
                        unavailable.append(cert)
                else:
                    # logger.warning(f"No information available for {cert}")
                    print(f"No information available for {cert}")
        else:
            pass


if __name__ == "__main__":
    typer.run(main)
