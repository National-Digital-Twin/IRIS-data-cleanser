"""Used to confim authorization key"""

import logging

import pandas as pd
import requests
import typer
from requests.adapters import HTTPAdapter, Retry
from sqlalchemy import create_engine

REQUEST_TIMEOUT = 500
MAX_PAGE_SIZE = 250
REQUEST_SLEEP = 0.5
BASE_URL = "https://epc.opendatacommunities.org/api/v1/non-domestic/search"
CONSTITUENCIES = [
    "E14000534",
    "E14000535",
    "E14000536",
    "E14000545",
    "E14000544",
    "E14000548",
    "E14000547",
    "E14000553",
    "E14000557",
    "E14000559",
    "E14000560",
    "E14000561",
    "E14000562",
    "E14000563",
    "E14000565",
    "E14000566",
    "E14000567",
    "E14000568",
    "E14000569",
    "E14000570",
    "E14000572",
    "E14000575",
    "E14000576",
    "E14000578",
    "E14000579",
    "E14000580",
    "E14000577",
    "E14000582",
    "E14000584",
    "E14000585",
    "E14000586",
    "E14000587",
    "E14000588",
    "E14000589",
    "E14000590",
    "E14000591",
    "E14000592",
    "E14000599",
    "E14000600",
    "E14000601",
    "E14000602",
    "E14000603",
    "E14000604",
    "E14000607",
]
AUTH_KEY = (
    "Basic "
    # pragma: allowlist nextline secret
    "amFtaWVAY29lZmZpY2llbnQuYWk6OTgwY2YxZTJiZGI4ZDhlMmY2M2M2YTU2ZjllMGY5ZTc3YzA2MzlmNw=="
)


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
        df, search_after = requests_cached(BASE_URL, params=params, logger=logger)

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
                    f"Reached 10000 records for constituency for {constituency}",
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
        write_to_db(segment_df, "england_nondomestic_certificates", db_config=db_config)
        # df_list.append(segment_df)

    # logger.info(f"{len(recommendations)} rows retrieved from the EPC API ✨")

    # return recommendations


if __name__ == "__main__":
    typer.run(main)
