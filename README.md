# IRIS Data Cleanser

[![CI](https://github.com/National-Digital-Twin/IRIS-data-cleanser/actions/workflows/main.yaml/badge.svg)](https://github.com/National-Digital-Twin/IRIS-data-cleanser/actions/workflows/main.yaml)

IRIS Data Cleanser - ETL pipeline using Airbyte, dbt (targeting Postgres), loading into S3.

## Project cheatsheet

  - **pre-commit:** `pre-commit run --all-files`
  - **pytest:** `pytest` or `pytest -s`
  - **coverage:** `coverage run -m pytest` or `coverage html`
  - **poetry sync:** `poetry install --no-root --sync`
  - **updating requirements:** see [docs/updating_requirements.md](docs/updating_requirements.md)
  - **create towncrier entry:** `towncrier create 123.added --edit`
  - **run license check:** `liccheck -s pyproject.toml -r requirements.txt > liccheck_report.txt && python -m convert_liccheck_report`


## Running local code development tools

See [RUNNING_CODE_DEV_TOOLS.md](./developer_docs/RUNNING_CODE_DEV_TOOLS.md) for more information.


## Initial project setup

1. See [docs/getting_started.md](docs/getting_started.md) or [docs/quickstart.md](docs/quickstart.md)
   for how to get up & running.
2. Check [docs/project_specific_setup.md](docs/project_specific_setup.md) for project specific setup.
3. See [docs/using_poetry.md](docs/using_poetry.md) for how to update Python requirements using
   [Poetry](https://python-poetry.org/).
4. See [docs/detect_secrets.md](docs/detect_secrets.md) for more on creating a `.secrets.baseline`
   file using [detect-secrets](https://github.com/Yelp/detect-secrets).
5. See [docs/using_towncrier.md](docs/using_towncrier.md) for how to update the `CHANGELOG.md`
   using [towncrier](https://github.com/twisted/towncrier).
