"""General Sparql endpoint to retrieve recommendation reports
from Q1 2014 to Q4 2023.
"""

import pathlib
import re
import tempfile
from itertools import chain
from os.path import realpath
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import requests
import typer
import yaml
from joblib import Memory
from SPARQLWrapper import JSON, SPARQLWrapper
from sqlalchemy import create_engine

CACHE_DIR = ".cache"
memory = Memory(CACHE_DIR, verbose=0)

with open(Path.home() / ".dbt/profiles.yml", encoding="utf-8") as file:
    CONFIG = yaml.safe_load(file)

db_config = CONFIG["c477_data_cleansing"]["outputs"]["dev_postgres"]


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


def get_domestic_cert_download_url():
    """Gets url to the download file"""

    query = """

                SELECT ?o
                FROM <http://statistics.gov.scot/graph/domestic-energy-performance-certificates/metadata>
                WHERE {
                ?s ?p ?o .
                FILTER(strStarts(str(?o), "http://statistics.gov.scot/downloads/file?id"))
                }
            """

    sparql = SPARQLWrapper("http://statistics.gov.scot/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    status = sparql.query().response.status
    assert status == 200, "Check Query and Endpoint"

    download_url = [i["o"]["value"] for i in results["results"]["bindings"]]
    return download_url[0], status


def get_domestic_download_name():
    """Gets download file name"""

    query = """

                SELECT ?o
                FROM <http://statistics.gov.scot/graph/domestic-energy-performance-certificates/metadata>
                WHERE {
                ?s ?p ?o .
                FILTER(strStarts(str(?o), "D_EPC"))
                }
            """
    sparql = SPARQLWrapper("http://statistics.gov.scot/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    status = sparql.query().response.status
    assert status == 200, "Check Query and Endpoint"

    download_name = [i["o"]["value"] for i in results["results"]["bindings"]]

    return download_name[0], status


def get_non_domestic_cert_download_url():
    """Gets url to the download file"""

    query = """

                SELECT ?o
                FROM <http://statistics.gov.scot/graph/non-domestic-energy-performance-certificates/metadata>
                WHERE {
                ?s ?p ?o .
                FILTER(strStarts(str(?o), "http://statistics.gov.scot/downloads/file?id"))
                }
            """

    sparql = SPARQLWrapper("http://statistics.gov.scot/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    status = sparql.query().response.status
    assert status == 200, "Check Query and Endpoint"

    download_url = [i["o"]["value"] for i in results["results"]["bindings"]]
    print(download_url)
    return download_url[0], status


def get_non_domestic_download_name():
    """Gets download file name"""

    query = """

                SELECT ?o
                FROM <http://statistics.gov.scot/graph/non-domestic-energy-performance-certificates/metadata>
                WHERE {
                ?s ?p ?o .
                FILTER(strStarts(str(?o), "ND_EPC"))
                }
            """
    sparql = SPARQLWrapper("http://statistics.gov.scot/sparql")
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    status = sparql.query().response.status
    assert status == 200, "Check Query and Endpoint"

    download_name = [i["o"]["value"] for i in results["results"]["bindings"]]
    return download_name[0], status


def create_column(x: str, key="key"):
    """Creates a dictionary from a string of format **column name: column value;"""
    x = re.sub("{&[a-z]+;}", "and", x)
    entries = [i for i in x.split("|") if len(i) > 1]
    for x in entries:
        if len(x) > 1:
            for i in x.split(";"):
                if len(i) > 1 and i.__contains__(":"):
                    yield {
                        i.split(":")[0].strip(): i.split(":")[1].strip(),
                        "BUILDING_REFERENCE_NUMBER": key,
                    }
                ##downside is it discards texts after;without:


def preproc_domestic(logger=None):
    """Preprocessing script for EPC backup"""
    dfs = []
    rec_dfs = []

    domestic_download_url, _ = get_domestic_cert_download_url()
    domestic_download_name, _ = get_domestic_download_name()

    ## headers contain next update date and last modified date
    with tempfile.TemporaryDirectory() as temp:
        temppath = pathlib.Path(temp)
        # Use requests to download the file instead of urlretrieve
        response = requests.get(domestic_download_url, stream=True)
        response.raise_for_status()

        domestic_path = temppath / domestic_download_name
        with open(domestic_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        headers = response.headers
        path_to_file = str(domestic_path)
    with ZipFile(path_to_file) as zf:
        files = [i for i in zf.namelist() if i.endswith(".csv")]
        for file in files:
            with zf.open(file) as myfile:
                df = pd.read_csv(myfile, low_memory=False)

                # removing alternative column names
                df = df.iloc[1:, :]

                # adding extra columns, and reconciling columns to match england and wales
                df.rename(
                    columns={
                        "WALL_ENV_EFF": "WALLS_ENV_EFF",
                        "WALL_ENERGY_EFF": "WALLS_ENERGY_EFF",
                    },
                )
                rec_df = df[~df["IMPROVEMENTS"].isna()]
                rec_df = pd.DataFrame(
                    chain.from_iterable(
                        create_column(i.IMPROVEMENTS, key=i.BUILDING_REFERENCE_NUMBER)
                        for i in rec_df.itertuples()
                    ),
                )
                # Add key to this, also update in connector
                rec_df.columns = [
                    "IMPROVEMENT_DESCR_TEXT",
                    "BUILDING_REFERENCE_NUMBER",
                    "INDICATIVE_COST",
                    "TYPICAL_SAVING",
                    "ENERGY_RATING_AFTER_IMPROVEMENT",
                    "ENVIRONMENTAL_RATING_AFTER_IMPROVEMENT",
                    "GREEN_DEAL_ELIGIBLE",
                ]
            dfs.append(df)
            rec_dfs.append(rec_df)
        scot_domestic_epc = pd.concat(dfs, axis=0, ignore_index=True)
        rec_dfs = pd.concat(rec_dfs, axis=0, ignore_index=True)
    return scot_domestic_epc, rec_dfs


def preproc_non_domestic(logger=None):
    """Preprocessing script for EPC backup"""
    rec_dfs = []
    non_domestic_download_url, _ = get_non_domestic_cert_download_url()
    non_domestic_download_name, _ = get_non_domestic_download_name()

    ## headers contain next update date and last modified date
    with tempfile.TemporaryDirectory() as temp:
        temppath = pathlib.Path(temp)
        # Use requests to download the file instead of urlretrieve
        response = requests.get(non_domestic_download_url, stream=True)
        response.raise_for_status()

        non_domestic_path = temppath / non_domestic_download_name
        with open(non_domestic_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        headers = response.headers

    path_to_file = realpath(non_domestic_path)
    dfs = []
    with ZipFile(path_to_file) as zf:
        files = [i for i in zf.namelist() if i.endswith(".csv")]
        for file in files:
            with zf.open(file) as myfile:
                df = pd.read_csv(myfile, low_memory=False)
                df = df.iloc[1:, :]
                rec_df = df[~df["IMPROVEMENT_RECOMMENDATIONS"].isna()]

                rec_df = pd.DataFrame(
                    chain.from_iterable(
                        create_column(
                            i.IMPROVEMENT_RECOMMENDATIONS,
                            key=i.BUILDING_REFERENCE_NUMBER,
                        )
                        for i in rec_df.itertuples()
                    ),
                )
                rec_df.columns = [
                    "CODE",
                    "BUILDING_REFERENCE_NUMBER",
                    "C02_IMPACT",
                    "PAYBACK_TYPE",
                    "IMPROVEMENT_DESCR_TEXT",
                ]
        dfs.append(df)
        rec_dfs.append(rec_df)
    scot_non_domestic_epc = pd.concat(dfs, axis=0, ignore_index=True)
    rec_dfs = pd.concat(rec_dfs, axis=0, ignore_index=True)
    write_to_db(
        scot_non_domestic_epc,
        table="scotland_nondomestic_certificates",
        exists="append",
        db_config=db_config,
    )
    write_to_db(
        rec_dfs,
        table="scotland_nondomestic_recommendations",
        exists="append",
        db_config=db_config,
    )
    return scot_non_domestic_epc, rec_dfs


def main():
    """Main pipeline runner"""
    domestic_df, rec_df = preproc_domestic()
    non_domestic_df, non_rec_df = preproc_non_domestic()

    return (domestic_df, rec_df), (non_domestic_df, non_rec_df)


if __name__ == "__main__":
    typer.run(get_non_domestic_cert_download_url)
