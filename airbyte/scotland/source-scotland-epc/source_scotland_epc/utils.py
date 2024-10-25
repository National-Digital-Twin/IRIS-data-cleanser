"""Get Scottish domestic/non-domestic certificates and recommendations from Q1 2014 to Q4 2023."""

import logging
import pathlib
import re
import tempfile
from itertools import chain
from zipfile import ZipFile

import pandas as pd
import requests
import typer
from loguru import logger as loguru_logger
from SPARQLWrapper import JSON, SPARQLWrapper


def get_download_url(property_type: str) -> tuple[str, int]:
    """Gets url to the download file + returns the download url and status"""

    # Lookup URL
    base_url = "http://statistics.gov.scot/graph"
    urls = {
        "domestic": f"{base_url}/domestic-energy-performance-certificates/metadata",
        "non-domestic": f"{base_url}/non-domestic-energy-performance-certificates/metadata",
    }
    url = urls[property_type]

    # Define the SPARQL query to fetch the download URL
    query = f"""
        SELECT ?o
        FROM <{url}>
        WHERE {{
            ?s ?p ?o .
            FILTER(strStarts(str(?o), "http://statistics.gov.scot/downloads/file?id"))
        }}
    """

    # Initialize the SPARQL wrapper with the endpoint URL
    sparql = SPARQLWrapper("http://statistics.gov.scot/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    # Execute the query and convert the results
    results = sparql.query().convert()

    # Check the status code of the response
    status = sparql.query().response.status
    assert status == 200, "Check Query and Endpoint"

    # Extract the download URL from the results
    download_url = [i["o"]["value"] for i in results["results"]["bindings"]]

    # Return the first (and only) download URL along with the status code
    return download_url[0], status


def get_download_name(property_type: str) -> tuple[str, int]:
    """Gets download file name for Scottish Energy Performance Certificates"""

    # Lookup URL
    base_url = "http://statistics.gov.scot/graph"
    urls = {
        "domestic": f"{base_url}/domestic-energy-performance-certificates/metadata",
        "non-domestic": f"{base_url}/non-domestic-energy-performance-certificates/metadata",
    }
    url = urls[property_type]
    codes = {
        "domestic": "D_EPC",
        "non-domestic": "ND_EPC",
    }
    code = codes[property_type]

    # Define the SPARQL query to fetch the download file name
    query = f"""
        SELECT ?o
        FROM <{url}>
        WHERE {{
            ?s ?p ?o .
            FILTER(strStarts(str(?o), "{code}"))
        }}
    """

    # Initialize the SPARQL wrapper with the endpoint URL
    sparql = SPARQLWrapper("http://statistics.gov.scot/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    # Execute the query and convert the results
    results = sparql.query().convert()

    # Check the status code of the response
    status = sparql.query().response.status
    assert status == 200, "Check Query and Endpoint"

    # Extract the download file name from the results
    download_name = [i["o"]["value"] for i in results["results"]["bindings"]]

    # Return the first (and only) download file name along with the status code
    return download_name[0], status


def create_column(x: str, key="key"):
    """Creates a dictionary from a string of format **column name: column value;"""
    x = re.sub("{&[a-z]+;}", "and", x)
    entries = [entry.strip() for entry in x.split("|") if entry.strip()]
    # Downside of this approach is it discards texts after ';' without ':'
    for entry in entries:
        if len(entry) > 1:
            for subentry in entry.split(";"):
                if len(subentry) > 1 and subentry.__contains__(":"):
                    yield {
                        subentry.split(":")[0].strip(): subentry.split(":")[1].strip(),
                        "BUILDING_REFERENCE_NUMBER": key,
                    }


def main(property_type: str, logger=None):
    """Main pipeline runner"""
    # Set up logging
    if logger == "loguru":
        logger = loguru_logger
    if not logger:
        logger = logging.getLogger("airbyte")

    assert property_type in ["domestic", "non-domestic"]
    improvements_col = {
        "domestic": "IMPROVEMENTS",
        "non-domestic": "IMPROVEMENT_RECOMMENDATIONS",
    }.get(property_type)

    # Initialize lists to store DataFrames
    dfs = []
    rec_dfs = []

    # Get download URL and file name
    download_url, _ = get_download_url(property_type=property_type)
    download_name, _ = get_download_name(property_type=property_type)

    # Create a temporary directory for file operations
    with tempfile.TemporaryDirectory() as temp:
        temppath = pathlib.Path(temp)

        # Download the file using requests
        response = requests.get(download_url, stream=True)
        response.raise_for_status()

        # Save the downloaded file
        file_path = temppath / download_name
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Headers contain next update date and last modified date
        headers = response.headers
        logger.info(
            f"{headers['Content-Length']} bytes downloaded "
            f"(last modified: {headers['Last-Modified']})",
        )

        # Check if the file was saved correctly
        if not file_path.exists():
            error_msg = f"File not found: {file_path}"
            raise FileNotFoundError(error_msg)

        # Process the downloaded ZIP file
        with ZipFile(file_path) as zf:
            # Get all CSV files in the ZIP
            files = [i for i in zf.namelist() if i.endswith(".csv")]
            for file in files:
                with zf.open(file) as myfile:
                    df = (
                        # Read CSV into DataFrame
                        pd.read_csv(myfile, low_memory=False)
                        # Remove alternative column names (first row)
                        .iloc[1:, :]
                        .rename(
                            # Rename columns to match England and Wales format
                            columns={
                                "WALL_ENV_EFF": "WALLS_ENV_EFF",
                                "WALL_ENERGY_EFF": "WALLS_ENERGY_EFF",
                            },
                        )
                    )

                    # Process improvements data
                    rec_df = df[~df[improvements_col].isna()]
                    rec_df = pd.DataFrame(
                        chain.from_iterable(
                            create_column(
                                getattr(i, improvements_col),
                                key=i.BUILDING_REFERENCE_NUMBER,
                            )
                            for i in rec_df.itertuples()
                        ),
                    )

                    # Set column names for improvements DataFrame
                    if property_type == "domestic":
                        rec_df.columns = [
                            "IMPROVEMENT_DESCR_TEXT",
                            "BUILDING_REFERENCE_NUMBER",
                            "INDICATIVE_COST",
                            "TYPICAL_SAVING",
                            "ENERGY_RATING_AFTER_IMPROVEMENT",
                            "ENVIRONMENTAL_RATING_AFTER_IMPROVEMENT",
                            "GREEN_DEAL_ELIGIBLE",
                        ]
                    else:
                        rec_df.columns = [
                            "CODE",
                            "BUILDING_REFERENCE_NUMBER",
                            "C02_IMPACT",
                            "PAYBACK_TYPE",
                            "IMPROVEMENT_DESCR_TEXT",
                        ]

                    # Yield the processed DataFrame
                    dfs.append(df)
                    rec_dfs.append(rec_df)

    epc_certificates = pd.concat(dfs, axis=0, ignore_index=True)
    epc_recommendations = pd.concat(rec_dfs, axis=0, ignore_index=True)

    epc_certificates["DOMESTIC"] = property_type
    epc_recommendations["DOMESTIC"] = property_type

    # Return processed DataFrames
    return epc_certificates, epc_recommendations


if __name__ == "__main__":
    typer.run(main)
