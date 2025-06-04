# SPDX-License-Identifier: Apache-2.0
# © Crown Copyright 2025. This work has been developed by the National Digital Twin Programme
# and is legally attributed to the Department for Business and Trade (UK) as the governing entity.

"""
Example Usage:

python -m address_base_plus_s3_export --input_file mart_parity_address_profiling.csv
dbt run -s address_base_plus_s3_export
"""

import logging
import os
from datetime import datetime
from io import StringIO

import boto3
import typer
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from dotenv import load_dotenv

# load credentials from .env
load_dotenv(".env", verbose=True)

SKIP_S3_UPLOAD = os.environ.get("SKIP_S3_UPLOAD", True)
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
AWS_REGION_NAME = os.environ.get("AWS_REGION_NAME")
DEBUG = os.environ.get("DEBUG", False)

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.ERROR,
    format="%(asctime)s - %(levelname)s %(message)s",
)


def export(df):
    """Export final mart to s3."""

    if SKIP_S3_UPLOAD:
        logging.info("-" * 100, "SKIPPING S3 UPLOAD", "-" * 100)
        return df

    # connect to s3
    logging.info("CONNECTING TO S3")
    try:
        s3_client = boto3.client(
            "s3",
            region_name=AWS_REGION_NAME,
        )
        logging.info("Successfully connected to s3")
    except (NoCredentialsError, PartialCredentialsError) as e:
        typer.echo(f"Error with AWS credentials: {str(e)}")
        return None

    bucket_name = S3_BUCKET_NAME
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    user_string = f"{user}_" if (user := os.environ.get("S3_FILENAME_USER")) else ""
    object_key = f"address_base_plus_{user_string}{timestamp}.csv"

    # check bucket exists
    logging.info("CHECKING S3 BUCKET EXISTS")
    try:
        # Check if the bucket exists and is accessible
        s3_client.head_bucket(Bucket=bucket_name)
        logging.info("Successfully connected to bucket")
    except ClientError as e:
        typer.echo(f"Error: Could not access the S3 bucket: {e}")
        return None

    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)

    # upload file
    logging.info("UPLOADING FILE")
    try:
        response = s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=csv_buffer.getvalue(),
        )
        # Log the successful upload
        typer.echo(
            f"Successfully uploaded `{object_key}` to S3 bucket `{bucket_name}`. ✨"
        )
        return response
    except ClientError as e:
        typer.echo(f"Error uploading file to S3: {e}")
        return None


def model(dbt, fal):
    """Interoperate with dbt fal's dbt run command."""
    df = dbt.ref("mart_address_base_plus")
    export(df)
    return df


def main(input_file: str):
    """Interoperate with python cli call."""
    return export(input_file)


if __name__ == "__main__":
    typer.run(main)
