# Using Python with dbt

This how-to guide shows you how to integrate Python with dbt's structured data modelling approach to improve your data transformation processes. It assumes that you have a good understanding of how dbt functions to execute all the steps outlined below. You should also have access to one of the data warehouse supported by dbt, which is either of Snowflake, Databricks, BigQuery, or fal.

## [Prerequisites](#prerequisites)

- Ensure that Python is installed by running the following command in your command line interface (CLI):
`python --version` If you need to install Python, visit the official Python website for your operating system's installation instructions.

- Verify your access to a data warehouse that dbt supports, such as Snowflake, Databricks, BigQuery, or one compatible with 'dbt-fal' by logging into the respective service.

- To confirm your understanding of dbt, consider reviewing the dbt documentation or completing a beginner's tutorial to familiarise yourself with its core concepts and functionalities.



## [General Steps](#general-steps)


This section shows you how to set up a virtual environment for dbt and initialise a new project tailored for Python-based data transformations.

<b>Installation and setup </b>

- (Optional) If you want to isolate your dbt project's dependencies, create a virtual environment using Python's venv module and activate it before installing dbt.

- Once your virtual environment is active, install dbt core by running pip install dbt. To begin setting up your dbt project, use the command dbt init and then navigate to the project directory that has been created.

- Define Python models: To define a Python model for your data transformations, write a Python function. For example, a simple Python model might look like this:

```python
def model(dbt, session):
…
return transformed_dataframe

```
- If you need to reference other models (SQL or Python) or sources in your Python code, use ```dbt.ref('model_name') ```

- If you want to read directly from a raw source table, use ```dbt.source('source_name', 'table_name')``` to refer to a source table.

These methods return a DataFrame pointing to the upstream source:
```
def model(dbt, session):
    upstream_model = dbt.ref(“upstream_model_name”)
    upstream_source = dbt.source(“upstream_source_name”, “table_name”)
    …
```
There are three ways to configure Python models:

- Option 1: In `dbt_project.yml` file, where you can configure many models at once.

- Option 2: In a dedicated `<model-name>.yml` file corresponding to `<model-name>.sql`, within the `models/` directory. Example:

```yaml
models:
 - name: <model-name> #change this
   description: "A dbt model for ..."


   config:
     materialized: table
     tags: ['python']
```
- Option 3: Within the model’s .py file, using the dbt.config() method. Example:

```
def model(dbt, session):
   # setting configuration
   dbt.config(materialized="table")
```

Remember, ‘table’ and ‘incremental’ are the only materialization options available for Python models in dbt.

Choose a data warehouse that fits your project requirements, such as Snowflake, Databricks, or BigQuery. Your choice will determine the specific dbt adapter to install, so make sure to refer to the dbt documentation for guidance on installing the appropriate adapter for your selected warehouse.


<b>Integrating Python with dbt:</b>

<b>Cloud </b>

Cloud platforms like BigQuery, Snowflake, and Databricks offer their own unique connectors or integrations to execute Python code right within the data warehouse environment.

How it works: To use Python with these platforms, you configure dbt to operate with the data warehouse's specific Python runtime. This could involve using proprietary features like User-Defined Functions (UDFs) or external scripts.

<b>Local  </b>

The dbt-fal library is a dbt package built specifically to run Python scripts locally as part of the dbt workflow.

How it works: With dbt-fal, data is downloaded from the database to your local system, manipulated using Python, and then the transformed data is uploaded back to the database. This gives you the versatility to use all of Python's capabilities, including any libraries and modules that might not be supported by your cloud service's environment.

So, while cloud services provide ease of use within their controlled environments, dbt-fal offers the freedom to use the expansive Python ecosystem right from your local machine.

## [Adapter Specific Steps](#adapter-specific-steps)

This section shows you how to install and configure the specific dbt adapters (Snowflake, Databricks, BigQuery and dbt-fal) that connect dbt to your chosen data warehouse.

<br></br>

### [Snowflake](#snowflake)
<br></br>

<b>Account Setup </b>

- Begin by creating or logging into an account on Snowflake.
After logging in, change your role to ‘ORGADMIN’. This role is required to modify account-level settings, including enabling features such as Anaconda Python packages.
- Navigate to the Billing & Terms tab to enable Anaconda Python packages. This step allows you to use Python packages in Snowflake - a prerequisite for using dbt with Python.
- Use the Worksheets tab to create your working environment. This involves creating a database, a schema within that database, and a warehouse to perform computations:
```
create database epc;
create schema epc.coefficient;
create warehouse epc_wh;
```
These resources are important for organising your data and providing the computational resources to execute your queries and transformations.

<b>dbt configuration for Snowflake</b>

- With your virtual environment activated, install the Snowflake adapter for dbt using `pip install dbt-snowflake`

- Set up your dbt profile by editing the <b>~/.dbt/profiles.yml</b> file. This file tells dbt how to connect to your data warehouse with the correct credentials and connection details. The profile should match the structure expected by dbt for Snowflake connections. Example:
```
epc:
  outputs:
    dev:
      account: <your-account-id> #change this
      database: epc
      password: <your-password> #change this
      role: ACCOUNTADMIN
      schema: coefficient
      threads: 1
      type: snowflake
      user: <your-user> #change this
      warehouse: epc_wh
  target: dev
```

Change `<your-user>` and `<your-password>` to the user and password of your snowflake account. You can find `<your-account-id>` in accounts inside the admin tab.

- In the <b>models</b> directory, create Python files to define your data models. Remember, Snowflake defaults to Snowpark DataFrames (similar to Apache Spark, but within Snowflake), so import the necessary library before writing functions.
```
import snowflake.snowpark.functions as F
# Define your Python dbt model here
```
- Run `dbt build`

<br></br>

### [Databricks](#databricks)

<br></br>

<b>Environment Setup</b>

- Start by creating an account with a cloud provider that supports Databricks, such as GCP, AWS, or Azure. You will use their infrastructure to run your Databricks instance.

- With the cloud provider selected, sign up for a Databricks account, opting for the Premium plan to ensure access to all the features.

- In the workspace setup, assign a name to your workspace, select the appropriate region, and click the "quickstart" button.
On the following page, create a strong password, acknowledge the terms, and click "create stack" to finalize the workspace setup.

- After creating your workspace, there are three key pieces of information you need <b> to note down</b>:

- + Server hostname and HTTP path: These warehouse connection details are required to establish a connection with dbt and execute commands in your Databricks workspace. This is located under the SQL Warehouses section.
- + Cluster ID: Required to define where dbt jobs will run. Create a cluster under the Data Science & Engineering tab and record the cluster ID from the URL.

- + Account Token: A secure way for dbt to authenticate with Databricks. This is generated in the User Settings section. Remember to store this securely as it's required for dbt configuration and cannot be retrieved once created.

<b>dbt Configuration for Databricks</b>

- With your virtual environment activated, install the Databricks adapter for dbt using `pip install dbt-databricks.`

- Edit or create the <b>~/.dbt/profiles.yml</b> file to include the Databricks connection details.
```
epc:
  outputs:
    dev:
      catalog: null
      host: [your-host-name]
      http_path: [your-http-path]
      schema: coefficient
      threads: 1
      token: [your-access-token]
      type: databricks
  target: dev
```
- In the <b>models</b> directory, create Python files to define your data models. Remember, Databricks defaults to Apache Spark DataFrames, so import the necessary library before writing functions.
```
import pyspark.sql.functions as F
# Define your Python dbt model here
```

- Choose one of the following submission methods for your models:

- + All_purpose_cluster (default):  Uses a constant cluster that's always available, leading to quicker execution times.

- + Job Cluster: This option only creates a cluster when it's needed for a job. It's a cost-effective approach as it doesn't maintain a constant cluster, however the job execution time can be delayed as clusters need to be set up and terminated each time.

- For each model, configure the submission method using either of the submission methods mentioned previously, to define how your model runs on Databricks:
```
def model(dbt, session):
    dbt.config(
      submission_method="all_purpose_cluster",
      create_notebook=True,
      cluster_id="abcd-1234-wxyz"
    )
    # Model logic here
```
or  in <b>dbt_project.yml</b>
```
models:
 project_name:
   subfolder:
     # set defaults for all .py models defined in this subfolder
     +submission_method: all_purpose_cluster
     +create_notebook: False
     +cluster_id: abcd-1234-wxyz
```

```
models:
  - name: my_python_model
    config:
      submission_method: job_cluster
      job_cluster_config:
      spark_version: ...
      node_type_id: ...
```

- Run `dbt build`

<br></br>

### [Google BigQuery](#google-bigquery)

<br></br>

<b> Account Setup </b>

- Sign up to the Google Cloud Platform (GCP) and create a new project within the GCP console. This project will contain all your related cloud resources.

- Navigate to IAM & Admin > Service Accounts and create a Service Account (SA) for dbt. The SA acts as an identity for dbt to interact with GCP services securely.

- Assigning roles and creating keys:
- + While you can give the SA broad permissions with roles like Resource Admin, it is recommended to assign only the necessary permissions for increased security. To follow the principle of least privilege, you can check what are the exact needed permissions [here](https://docs.getdbt.com/guides/bigquery?step=1).

- + Navigate to Actions > Manage keys > Add Key > Create new key, select JSON, and download the file. This key file will authenticate dbt with GCP and should be kept safe.
Create a cloud storage bucket to store temporary data and other artifacts. Choose the same region as your future resources to optimise access speeds and costs.


- Find the Dataproc API in the Marketplace and enable it. Dataproc will run and manage your Spark jobs for dbt’s Python models.

- Create a new cluster in Dataproc, choosing the same region as your storage bucket to minimize latency and costs. Opt for machine types such as <b>n1-standard-2</b> to stay within default quotas and control expenses.

Remember: When initializing your cluster, include connector scripts that allow Dataproc to work with BigQuery. You can do this by inserting the provided initialization action and metadata into the respective fields. While Google suggests storing this info in a bucket for production environments, for the sake of this how-to guide, we input them directly into the cluster properties.

<b>dbt Configuration for BigQuery</b>

- With your virtual environment activated, install the BigQuery adapter for dbt using `pip install dbt-bigquery`

- Edit or create the <b>~/.dbt/profiles.yml</b> file to contain your GCP project ID, the SA key file’s path, and the details about the Dataproc cluster. This profile acts as dbt’s roadmap for connecting to your data warehouse and executing models. Example:
```
epc:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: service-account-json
      project: [your-project-id]
      dataset: epc
      threads: 1




      # These fields come from the service account json keyfile
      keyfile_json:
        type: xxx
        project_id: xxx
        private_key_id: xxx
        private_key: xxx
        client_email: xxx
        client_id: xxx
        auth_uri: xxx
        token_uri: xxx
        auth_provider_x509_cert_url: xxx
        client_x509_cert_url: xxx




      # for dbt Python models
      gcs_bucket: [the-name-of-your-bucket]
      dataproc_region: [your-region] #e.g.: us-east1
```

- In the <b>models</b> directory, write Python files where you will define your data models. As these models will run as PySpark jobs, you need to ensure they are compatible with the BigQuery and Dataproc platforms by importing this function:

```
import pyspark.sql.functions as F
# Define your Python dbt model here
```
- Choose one of the submission methods for your models:

+ + <u>serverless</u>: This doesn't need a pre-existing cluster, however, it may have startup delays and limited Python package availability.

- + <u>cluster</u>: Configuring a Dataproc cluster beforehand gives you control over its settings and allows installation of custom Python packages, ensuring a more responsive system.

- Specify the submission_method either within individual Python models. Example:
```
def model(dbt, session):
    dbt.config(
      submission_method="cluster",
      dataproc_cluster_name="my-dataproc-cluster"
    )
    # Python model code

```
or globally in the <b>dbt_project.yml</b> file

- Run `dbt build`

<br></br>

### [dbt-fal](#dbt-fal)

<br></br>

<b> Setup</b>

Since ‘fal’ uses existing dbt adapters, pick one that matches your data warehouse. For this guide, we assume that you are using the BigQuery adapter, which means that you should have a GCP project and a service account set up. Refer to the initial steps in the BigQuery setup section information on setting this up

<b> dbt Configuration for fal</b>

- With your virtual environment active, we first install the fal adapter for dbt by running the command `pip install dbt-fal`

Note: Starting from version 1.8, installing an adapter like dbt-fal does not automatically include dbt-core. We need to install dbt-core separately to ensure our versions are aligned.

- After installing dbt-fal, proceed to `pip install dbt-bigquery `and `pip install pyarrow` to ensure all necessary components for the BigQuery integration are in place.

- Next, we need to edit or create the <b>~/.dbt/profiles.yml</b> file to configure our dbt environment. This setup will be similar to a standard BigQuery profile but will specify an output type of 'fal', which then points to BigQuery. Example:
```
Epc:
  target: dev_with_fal
  Outputs:
      Dev_with_fal:
        type: fal
        db_profile: dev_bq # This points to your main adapter
      Dev_bq:
        type: bigquery
        ...
```
- The key file generated during the GCP setup will authenticate dbt with BigQuery. We must secure this key as it's essential for our dbt project to communicate with GCP services.


- In the <b>models</b> directory, create Python files to define your data models.
Unlike SQL models, the use of fal allows us to harness the flexibility of Pandas dataframes. Example code:
```
def model(dbt, fal):
    """dbt-fal model."""
    epc = dbt.ref("stg_uk_epc_certificates")
    epc["uprn"] = epc["uprn"].apply(lambda x: np.nan if x == "" else x)


    os = dbt.ref("stg_uk_os")
    os["address"] = os["address"].str.lower()
    os["udprn"] = os["udprn"].apply(lambda x: np.nan if x in ["", "N/A"] else x)


    return pipeline(epc=epc, os=os)
```
- Run `dbt build`


### <b>[Best practices:](#best-practices)</b>

- <u>Organising your Python Models in dbt</u>: To use Python for data transformations, place your Python files in the 'models' directory of your dbt project. Remember to translate any SQL logic into Python, considering syntax and function differences that are specific to the libraries used by your data warehouse's adapter.

- <u>Executing your Python Models in dbt</u>: After adding your Python scripts to the dbt 'models' directory, perform data transformations by running dbt build from your project directory. To ensure everything is working correctly, keep an eye on the dbt logs for any errors. Once the dbt run is successful, your data will be updated in your warehouse as per your transformations.

<b>Need more help?</b>
For troubleshooting or to understand the process in greater detail, refer to the official dbt documentation. Additionally, for adapter-specific instructions and options, consult the [documentation](https://docs.getdbt.com/) for the dbt adapter you're using.
