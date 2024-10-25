"""Copyright (c) 2023 Airbyte, Inc., all rights reserved."""

import sys

from airbyte_cdk.entrypoint import launch
from source_scotland_epc import SourceScotlandEpc

if __name__ == "__main__":
    source = SourceScotlandEpc()
    launch(source, sys.argv[1:])
