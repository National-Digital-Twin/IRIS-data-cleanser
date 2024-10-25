# How to create custom connectors in Airbyte using Python

## Part 1: Setting Up a Python CDK Connector in Airbyte


### <b> [Prerequisites](#prerequisites) </b>


This guide assumes you are familiar with Airbyte concepts and have experience building a connector using the Connector builder. We’ll be extending this knowledge to implement connectors with the Python CDK, which is useful for incorporating advanced features not yet present in the Connector Builder.
Make sure you have Python, poetry, and Docker installed on your machine. These tools are critical dependencies for developing with the Python CDK.


### <b> [General Steps for Connector Development](#general-steps-for-connector-development) </b>

- After cloning the Airbyte repository, generate a template by running the generate.sh script. When prompted, select the Python CDK Source and name your connector <b>python-http-example.</b>


- Navigate to the connector's directory with `cd connectors/source-python-http-example` and set up your environment with `poetry install`.


- Define the input schema for your connector by editing the `spec.yaml` file. This schema depends on the specifics of the API you’ll be working with.


- In the `source.py` file, add a new class representing a data stream from an API you wish to connect to.


- Define your output schema for each stream by creating a JSON file in the `/source_python_http_example/schemas` directory.  This schema must precisely detail the expected output from the API endpoint, as Airbyte requires clear expectations for stream output.  For detailed insights, refer to the schema creation documentation [here](https://docs.airbyte.com/connector-development/cdk-python/schemas).


- To allow Airbyte to read from the source, create a catalog file as outlined in the template found [here](https://docs.airbyte.com/understanding-airbyte/beginners-guide-to-catalog).

- Place this file in `/sample_files` and name it `configured_catalog.json`. This catalog file informs Airbyte of the streams your connector supports and the sync modes it can operate in. You can learn more about sync modes [here](https://docs.airbyte.com/using-airbyte/core-concepts/sync-modes/).


There are two main approaches to containerize your connector for use in the Airbyte UI:


- Method 1 <b>(preferred)</b>: Building the docker image with airbyte-ci

This method is encouraged, especially if you plan to open source your connector. It builds from the Airbyte base image without relying on a Dockerfile.


```
airbyte-ci connectors --name source-<source-name> build
```
Build image with above command, which will then be available on your local docker host labeled as `airbyte/source-<source-name>:dev.`

- Method 2: Building the docker image with a Dockerfile

You can create your own <b>Dockerfile</b> in the root of your connector directory, then build your image with the following Docker command:

```
docker build . -t airbyte/source-example-python:dev
```

After the build process, you should have a local Docker image of your connector, ready to be used within the Airbyte UI.

## Part 2: Coefficient’s Approach

We included a standalone utils.py file within the <source_directory_name> as specified by airbyte when building a custom connector in <b>Part 1</b>. After, we imported the content of utils.py into source.py with this code block

```python
from . import utils

```
utils.py is a python script which contains custom code to scrap from a custom source. Custom source could be a sparql endpoint, a csv located in an s3 bucket, a html website, etc


#### <b>Benefits of including a standalone utils.py</b>

- Allows us to leverage Typer for rapid development in CLI when aligning stream output schema with specified json_schema in the discover method of `class Source`.
Note: The discover method returns an AirbyteCatalog object which describes a list of all available streams, thus it is important that the schema of a stream matches json_schema in the discover method of `class Source` for a successful run of the custom connector.
- In line with the DRY principle of writing maintainable code such that respective functions can be reused within `def check`, `def discover`,`def read` of Airbyte's base class `class Source`


`def check` : Tests, if the input configuration can be successfully used to connect to the integration.
In the example below, we used a hack to satisfy airbyte’s requirement of a configuration json as an input parameter to the check method.
We did this by adding an empty config.json to the docker build, while using the response from a function in utils.py to create a valid AirbyteConnectionStatus object

```

try:
    _, status = utils.get_domestic_cert_download_url()
    if status == 200:
        return AirbyteConnectionStatus(status=Status.SUCCEEDED)

        return AirbyteConnectionStatus(
                status=Status.FAILED,
                message=f"Authorization failed with status {status}",
            )
except Exception as e:
    return AirbyteConnectionStatus(
        status=Status.FAILED,
        message=f"An exception occurred: {e!s}")

```

`def read`: performs the syncing process from source to destination with a generator of the AirbyteMessages.

The generator of AirbyteMessages is created from a list of dictionaries, where each element of the list represents a row in the final table.

In the code snippet below, the heavy lifting has been abstracted to function `main` within utils.py which contains the custom code logic for our custom connector.

```

for rows in utils.non_domestic_recommendations(auth_key=config["auth_key"], logger=logger):
    logger.info(f"Yielding {len(rows)} AirbyteMessage records")
    for row in rows.to_dict(orient="records"):
        yield AirbyteMessage(type=Type.RECORD,
            record=AirbyteRecordMessage(
            stream=stream_name,
            data=row,
            emitted_at=int(datetime.now().timestamp()) * 1000,

```

Build the docker image, and publish to docker registry inorder to use it as a custom connector in airbyte. Preferred sync mode can then be further configured during the creation of connection
