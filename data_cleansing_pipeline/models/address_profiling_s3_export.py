# SPDX-License-Identifier: Apache-2.0
# © Crown Copyright 2025. This work has been developed by the National Digital Twin Programme
# and is legally attributed to the Department for Business and Trade (UK) as the governing entity.

"""
Example Usage:

python -m address_profiling_s3_export --input_file mart_parity_address_profiling_with_sap.csv
dbt run -s address_profiling_s3_export
"""

import os
from datetime import datetime
from io import StringIO

import boto3
import typer

from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

from pathlib import Path
from dotenv import load_dotenv


def export(df):
    """Export final mart to s3."""

    # load aws credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    if credentials is None:
        raise NoCredentialsError
    frozen_credentials = credentials.get_frozen_credentials()

    # load credentials from .env
    load_dotenv('.env', verbose=True)

    try:
        print("s3 upload flag:", os.environ.get("SKIP_S3_UPLOAD"))
        print(f"Using AWS Access Key: {frozen_credentials.access_key}")
        print(f"Using AWS Secret Access Key: {frozen_credentials.secret_key}")
        print("Using AWS token:", frozen_credentials.token)
        print("Using AWS Region:", os.environ.get("AWS_REGION_NAME"))
        print("Using Bucket Name:", os.environ.get("S3_BUCKET_NAME"))
    except:
        print("error loading .env file")

    if os.environ.get("SKIP_S3_UPLOAD") == True:
        print("-"*100, "SKIPPING S3 UPLOAD", "-"*100)
        return df

    # Check for missing environment variables
    print("CHECKING FOR MISSING ENV VARIABLES")
    required_vars = {
        "aws_credentials":[
            "access_key",
            "secret_key",
            "token"
            ],
        "other_secrets":[
            "S3_BUCKET_NAME",
        ]
    }
    for cred in required_vars["aws_credentials"]:
        value = getattr(frozen_credentials, cred)
        if not value:
            print(f"❌ {cred} is missing or empty!")
        else:
            print(f"✅ {cred} is present")
    for var in required_vars["other_secrets"]:
        if not os.environ.get(var):
            typer.echo(f"Error: Environment variable {var} is missing!")
            return None  # Return or handle as needed

    # connect to s3
    print("CONNECTING TO S3")
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=frozen_credentials.access_key,
            aws_secret_access_key=frozen_credentials.secret_key,
            aws_session_token=frozen_credentials.token,
            region_name=os.environ.get("AWS_REGION_NAME"),
        )
        print("Successfully connected to s3")
    except (NoCredentialsError, PartialCredentialsError) as e:
        typer.echo(f"Error with AWS credentials: {str(e)}")
        return None

    bucket_name = os.environ.get("S3_BUCKET_NAME")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    user_string = f"{user}_" if (user := os.environ.get("S3_FILENAME_USER")) else ""
    object_key = f"address_profiling_{user_string}{timestamp}.csv"

    # check bucket exists
    print("CHECKING S3 BUCKET EXISTS")
    try:
        # Check if the bucket exists and is accessible
        s3_client.head_bucket(Bucket=bucket_name)
        print("Successfully connected to bucket")
    except ClientError as e:
        typer.echo(f"Error: Could not access the S3 bucket: {e}")
        return None

    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)

    # upload file
    print("UPLOADING FILE")
    try:
        response = s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=csv_buffer.getvalue(),
        )
        # Log the successful upload
        typer.echo(f"Successfully uploaded `{object_key}` to S3 bucket `{bucket_name}`. ✨")
        return response
    except ClientError as e:
        typer.echo(f"Error uploading file to S3: {e}")
        return None


def model(dbt, fal):
    """Interoperate with dbt fal's dbt run command."""
    print("-"*100, "s3 export model", "-"*100)
    df = dbt.ref("mart_address_profiling_with_sap")
    print("-"*100, "Address profiling data", "-"*100)
    print(df.columns)
    print(df.shape)
    export(df)
    return df


def main(input_file: str):
    """Interoperate with python cli call."""
    return export(input_file)


if __name__ == "__main__":
    typer.run(main)
