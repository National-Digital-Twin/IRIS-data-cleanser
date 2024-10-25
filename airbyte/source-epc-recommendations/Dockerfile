FROM python:3.11 as base

# build and load all requirements
FROM base as builder
WORKDIR /airbyte/integration_code

# upgrade pip to the latest version
RUN apt-get update \
    && apt-get -y upgrade \
    && pip install --upgrade pip \
    && apt-get install -y tzdata build-essential libstdc++6

COPY setup.py ./
# install necessary packages to a temporary folder
RUN pip install --prefix=/install .

# build a clean environment
FROM base
WORKDIR /airbyte/integration_code

# copy all loaded and built libraries to a pure basic image
COPY --from=builder /install /usr/local

# add default timezone settings
# COPY --from=builder /usr/share/zoneinfo/Etc/UTC /etc/localtime
# RUN echo "Etc/UTC" > /etc/timezone

# bash is installed for more convenient debugging.
RUN apt-get update && apt-get -y install bash

# copy payload code only
COPY main.py ./
COPY source_epc_recommendations ./source_epc_recommendations

ENV AIRBYTE_ENTRYPOINT "python /airbyte/integration_code/main.py"
ENTRYPOINT ["python", "/airbyte/integration_code/main.py"]

LABEL io.airbyte.version=0.1.0
LABEL io.airbyte.name=airbyte/source-epc-recommendations
