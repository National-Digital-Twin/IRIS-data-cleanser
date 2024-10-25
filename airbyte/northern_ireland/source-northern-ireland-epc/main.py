"""Copyright (c) 2023 Airbyte, Inc., all rights reserved."""

import sys

from airbyte_cdk.entrypoint import launch
from source_northern_ireland_epc import SourceNIEpc

if __name__ == "__main__":
    source = SourceNIEpc()
    launch(source, sys.argv[1:])
