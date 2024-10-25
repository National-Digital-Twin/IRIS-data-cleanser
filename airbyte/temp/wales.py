"""Used to confim authorization key"""

import logging

import numpy as np
import pandas as pd
import requests
import typer
from requests.adapters import HTTPAdapter, Retry
from sqlalchemy import create_engine

REQUEST_TIMEOUT = 500
MAX_PAGE_SIZE = 250
REQUEST_SLEEP = 0.5
BASE_URL = "https://epc.opendatacommunities.org/api/v1"
DOMESTIC_URL = f"{BASE_URL}/domestic/search"
NON_DOMESTIC_URL = f"{BASE_URL}/non-domestic/search"
AUTH_KEY = (
    "Basic "
    # pragma: allowlist nextline secret
    "amFtaWVAY29lZmZpY2llbnQuYWk6OTgwY2YxZTJiZGI4ZDhlMmY2M2M2YTU2ZjllMGY5ZTc3YzA2MzlmNw=="
)

CONSTITUENCIES = [
    "W07000049",
    "W07000043",
    "W07000057",
    "W07000073",
    "W07000076",
    "W07000050",
    "W07000051",
    "W07000080",
    "W07000079",
    "W07000067",
    "W07000066",
    "W07000064",
    "W07000062",
    "W07000059",
    "W07000070",
    "W07000042",
    "W07000061",
    "W07000046",
    "W07000045",
    "W07000071",
    "W07000054",
    "W07000063",
    "W07000069",
    "W07000055",
    "W07000056",
    "W07000074",
    "W07000075",
    "W07000065",
    "W07000052",
    "W07000048",
    "W07000047",
    "W07000053",
    "W07000060",
    "W07000078",
    "W07000044",
    "W07000041",
]


def requests_cached(url, params, logger):
    """Wrapper for caching requests."""
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))

    headers = {
        "Authorization": AUTH_KEY,
        "Accept": "application/json",
    }
    response = s.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)

    search_after = response.headers.get("X-Next-Search-After")
    if response.status_code == 500:
        message = f"Encountered error 500 for {params=}"
        logger.error(message)
        raise RuntimeError(message)

    elif response.status_code == 200:
        df = pd.DataFrame(response.json()["rows"])
        return df, search_after

    else:
        message = f"Encountered error {response.status_code} for {params=}"
        logger.error(message)
        raise RuntimeError(message)

    return response


def check():
    """Checking schema of"""
    response = requests_cached(NON_DOMESTIC_URL, "W07000041")
    print(response.json())


# def requests_cached(params, logger, auth_key=None):
#     """Wrapper for caching requests."""
#     if not auth_key:
#         auth_key = AUTH_KEY

#     headers = {
#         "Accept": "application/json",
#         "Authorization": auth_key,
#     }

#     s = requests.Session()
#     retries = Retry(
#         total=10,
#         backoff_factor=1,
#         status_forcelist=[429, 500, 502, 503, 504],
#     )
#     s.mount("http://", HTTPAdapter(max_retries=retries))
#     s.mount("https://", HTTPAdapter(max_retries=retries))

#     response = s.get(DOMESTIC_URL, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
#     sleep(REQUEST_SLEEP)

#     if response.status_code == 500:
#         message = f"Encountered error 500 for {params=}"
#         logger.error(message)
#         raise RuntimeError(message)

#     elif response.status_code == 200:
#         df = pd.read_json(response.json())
#         return df

#     else:
#         message = f"Encountered error {response.status_code} for {params=}"
#         logger.error(message)
#         raise RuntimeError(message)


def fetch_recommendations_for_segment(logger, constituency, auth_key=None):
    """Fetch recs."""
    from_param = 0
    df_list = [pd.DataFrame()]

    first_request = True
    search_after = None
    while first_request or search_after is not None:
        params = {
            "constituency": constituency,
            "size": MAX_PAGE_SIZE,
            "from": from_param,
        }
        if search_after is not None:
            params["search-after"] = search_after
        df, search_after = requests_cached(DOMESTIC_URL, params=params, logger=logger)

        if df is None:
            break
        else:
            df_list.append(df)

        # If we fetched less than the maximum page size, we've reached the end.
        if df.shape[0] < MAX_PAGE_SIZE:
            break
        else:
            from_param += MAX_PAGE_SIZE
            if from_param >= 10000:
                logger.warning(
                    f"Reached 10000 records for {constituency}",
                )

    return pd.concat(df_list, axis=0, ignore_index=True)


db_config = {
    "user": "emmanuel",
    "host": "127.0.0.1",
    "port": "5332",
    "dbname": "postgres",
    "password": "ENTER SOMETHING HERE",  # pragma: allowlist secret
}


def write_to_db(df, table="destination", db_config=db_config):
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
            if_exists="append",
            chunksize=1000,
        )

    typer.echo(f"{len(df)} rows uploaded to {table} ✨")


def main(
    auth_key: str = None,
    logger=None,
) -> pd.DataFrame:
    """Main recommendations pipeline runner."""
    if not logger:
        logger = logging.getLogger("airbyte")

    df_list = []

    for constituency in CONSTITUENCIES:
        segment_df = fetch_recommendations_for_segment(
            constituency=constituency,
            logger=logger,
            auth_key=auth_key,
        )
        write_to_db(
            segment_df.replace({np.nan: None}),
            "wales_nondomestic_certificates_search",
            db_config=db_config,
        )
        # df_list.append(segment_df)

    # logger.info(f"{len(recommendations)} rows retrieved from the EPC API ✨")

    # return recommendations


if __name__ == "__main__":
    typer.run(main)
