"""Copyright (c) 2023 Airbyte, Inc., all rights reserved."""

from setuptools import find_packages, setup

MAIN_REQUIREMENTS = [
    "airbyte-cdk~=0.2",
    "numpy~=1.25.2",
    "pandas<2.0",
    "typer~=0.9.0",
    "sparqlwrapper==2.0.0",
    "urllib3==2.0.7",
    "loguru~=0.7.2",
]

TEST_REQUIREMENTS = [
    "requests-mock~=1.9.3",
    "pytest-mock~=3.6.1",
    "pytest~=6.2",
    "connector-acceptance-test",
]

setup(
    name="source_scotland_epc",
    description="Source implementation for Scottish certificates.",
    author="Airbyte",
    author_email="contact@airbyte.io",
    packages=find_packages(),
    install_requires=MAIN_REQUIREMENTS,
    package_data={"": ["*.json", "*.yaml"]},
    extras_require={
        "tests": TEST_REQUIREMENTS,
    },
)
