"""Copyright (c) 2023 Airbyte, Inc., all rights reserved."""

import json
from collections.abc import Generator
from datetime import datetime

import requests
from airbyte_cdk.logger import AirbyteLogger
from airbyte_cdk.models import (
    AirbyteCatalog,
    AirbyteConnectionStatus,
    AirbyteMessage,
    AirbyteRecordMessage,
    AirbyteStream,
    ConfiguredAirbyteCatalog,
    ConnectorSpecification,
    DestinationSyncMode,
    Status,
    Type,
)
from airbyte_cdk.sources import Source
from requests.adapters import HTTPAdapter, Retry

from . import utils


class SourceNIEpc(Source):
    def spec(self, logger: AirbyteLogger) -> ConnectorSpecification:
        """Returns the spec for this connector."""
        return ConnectorSpecification(
            documentationUrl="https://docs.airbyte.com/integrations/sources/source-northern-ireland-epc",
            changelogUrl="https://docs.airbyte.com/integrations/sources/source-northern-ireland-epc",
            supportsIncremental=True,
            supported_destination_sync_modes=[DestinationSyncMode.append],
            connectionSpecification={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "Norther Ireland EPC Certificates & Recommendations Spec",
                "type": "object",
                "required": [],
                "properties": {},
            },
        )

    def check(self, logger: AirbyteLogger, config: json) -> AirbyteConnectionStatus:
        """Tests if the input configuration can be used to successfully connect to the integration.

        :param logger: Logging object to display debug/info/error to the logs (logs will not be
            accessible via airbyte UI if they are not passed to this logger)
        :param config: Json object containing the configuration of this source, content of this json
            is as specified in the properties of the spec.yaml file

        :return: AirbyteConnectionStatus indicating a Success or Failure
        """
        try:
            headers = {"User-agent": "Mozilla/5.0"}

            s = requests.Session()
            retries = Retry(
                total=10,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            s.mount("http://", HTTPAdapter(max_retries=retries))
            s.mount("https://", HTTPAdapter(max_retries=retries))

            response = s.get(
                "https://find-energy-certificate.service.gov.uk/",
                headers=headers,
                timeout=500,
            )
            if response.status_code == 200:
                return AirbyteConnectionStatus(status=Status.SUCCEEDED)

            return AirbyteConnectionStatus(
                status=Status.FAILED,
                message=f"Authorization failed with status {response.status_code}",
            )
        except Exception as e:  # pylint: disable=invalid-name disable=broad-exception-caught
            return AirbyteConnectionStatus(
                status=Status.FAILED,
                message=f"An exception occurred: {e!s}",
            )

    def discover(self, logger: AirbyteLogger, config: json) -> AirbyteCatalog:
        """Returns an AirbyteCatalog representing the available streams and fields in this
        integration.

        For example, given valid credentials to a Postgres database, returns an Airbyte catalog
        where each postgres table is a stream, and each table column is a field.

        :param logger: Logging object to display debug/info/error to the logs (logs will not be
            accessible via airbyte UI if they are not passed to this logger)
        :param config: Json object containing the configuration of this source, content of this json
            is as specified in
        the properties of the spec.yaml file

        :return: AirbyteCatalog is an object describing a list of all available streams in this
            source. A stream is an AirbyteStream object that includes: - its stream name (or table
            name in the case of Postgres) - json_schema providing the specifications of expected
            schema for this stream (a list of columns described by their names and types)
        """
        streams = []
        stream_name = "northern_ireland_epc"

        fields = {
            "3_YR_ENERGY_COST_CURRENT": {"type": ["null", "string"]},
            "3_YR_ENERGY_SAVINGS_POTENTIAL": {"type": ["null", "string"]},
            "ADDENDUM_": {"type": ["null", "string"]},
            "ADDRESS1": {"type": ["null", "string"]},
            "ADDRESS2": {"type": ["null", "string"]},
            "ADDRESS3": {"type": ["null", "string"]},
            "AIR_TIGHTNESS_DESCRIPTION": {"type": ["null", "string"]},
            "AIR_TIGHTNESS_ENERGY_EFF": {"type": ["null", "string"]},
            "AIR_TIGHTNESS_ENV_EFF": {"type": ["null", "string"]},
            "ALTERNATIVE_IMPROVEMENTS": {"type": ["null", "string"]},
            "BUILDING_REFERENCE_NUMBER": {"type": ["null", "string"]},
            "BUILT_FORM": {"type": ["null", "string"]},
            "CO2_EMISSIONS_CURRENT": {"type": ["null", "string"]},
            "CO2_EMISSIONS_POTENTIAL": {"type": ["null", "string"]},
            "CO2_EMISS_CURR_PER_FLOOR_AREA": {"type": ["null", "string"]},
            "CONSTITUENCY": {"type": ["null", "string"]},
            "CONSTITUENCY_LABEL": {"type": ["null", "string"]},
            "CONSTRUCTION_AGE_BAND": {"type": ["null", "string"]},
            "CREATED_AT": {"type": ["null", "string"]},
            "CURRENT_ENERGY_EFFICIENCY": {"type": ["null", "string"]},
            "CURRENT_ENERGY_RATING": {"type": ["null", "string"]},
            "CURRENT_ENVIRONMENTAL_RATING": {"type": ["null", "string"]},
            "DATA_ZONE": {"type": ["null", "string"]},
            "DATA_ZONE_2011": {"type": ["null", "string"]},
            "ENERGY_CONSUMPTION_CURRENT": {"type": ["null", "string"]},
            "ENERGY_CONSUMPTION_POTENTIAL": {"type": ["null", "string"]},
            "ENERGY_TARIFF": {"type": ["null", "string"]},
            "ENVIRONMENT_IMPACT_CURRENT": {"type": ["null", "string"]},
            "ENVIRONMENT_IMPACT_POTENTIAL": {"type": ["null", "string"]},
            "EXTENSION_COUNT": {"type": ["null", "string"]},
            "FIXED_LIGHTING_OUTLETS_COUNT": {"type": ["null", "string"]},
            "FLAT_TOP_STOREY": {"type": ["null", "string"]},
            "FLOOR_DESCRIPTION": {"type": ["null", "string"]},
            "FLOOR_ENERGY_EFF": {"type": ["null", "string"]},
            "FLOOR_ENV_EFF": {"type": ["null", "string"]},
            "FLOOR_HEIGHT": {"type": ["null", "string"]},
            "FLOOR_LEVEL": {"type": ["null", "string"]},
            "GLAZED_AREA": {"type": ["null", "string"]},
            "GLAZED_TYPE": {"type": ["null", "string"]},
            "HEATING_COST_CURRENT": {"type": ["null", "string"]},
            "HEATING_COST_POTENTIAL": {"type": ["null", "string"]},
            "HEAT_LOSS_CORRIDOOR": {"type": ["null", "string"]},
            "HOTWATER_DESCRIPTION": {"type": ["null", "string"]},
            "HOT_WATER_COST_CURRENT": {"type": ["null", "string"]},
            "HOT_WATER_COST_POTENTIAL": {"type": ["null", "string"]},
            "HOT_WATER_ENERGY_EFF": {"type": ["null", "string"]},
            "HOT_WATER_ENV_EFF": {"type": ["null", "string"]},
            "IMPACT_CAVITY_WALL_INSULATION": {"type": ["null", "string"]},
            "IMPACT_LOFT_INSULATION": {"type": ["null", "string"]},
            "IMPACT_SOLID_WALL_INSULATION": {"type": ["null", "string"]},
            "INSPECTION_DATE": {"type": ["null", "string"]},
            "LIGHTING_COST_CURRENT": {"type": ["null", "string"]},
            "LIGHTING_COST_POTENTIAL": {"type": ["null", "string"]},
            "LIGHTING_DESCRIPTION": {"type": ["null", "string"]},
            "LIGHTING_ENERGY_EFF": {"type": ["null", "string"]},
            "LIGHTING_ENV_EFF": {"type": ["null", "string"]},
            "LOCAL_AUTHORITY_LABEL": {"type": ["null", "string"]},
            "LODGEMENT_DATE": {"type": ["null", "string"]},
            "LOW_ENERGY_FIXED_LIGHT_COUNT": {"type": ["null", "string"]},
            "LOW_ENERGY_LIGHTING": {"type": ["null", "string"]},
            "LZC_ENERGY_SOURCES": {"type": ["null", "string"]},
            "MAINHEATCONT_DESCRIPTION": {"type": ["null", "string"]},
            "MAINHEATC_ENERGY_EFF": {"type": ["null", "string"]},
            "MAINHEATC_ENV_EFF": {"type": ["null", "string"]},
            "MAINHEAT_DESCRIPTION": {"type": ["null", "string"]},
            "MAINHEAT_ENERGY_EFF": {"type": ["null", "string"]},
            "MAINHEAT_ENV_EFF": {"type": ["null", "string"]},
            "MAINS_GAS_FLAG": {"type": ["null", "string"]},
            "MAIN_FUEL": {"type": ["null", "string"]},
            "MAIN_HEATING_CATEGORY": {"type": ["null", "string"]},
            "MAIN_HEATING_CONTROLS": {"type": ["null", "string"]},
            "MECHANICAL_VENTILATION": {"type": ["null", "string"]},
            "MULTI_GLAZE_PROPORTION": {"type": ["null", "string"]},
            "NUMBER_HABITABLE_ROOMS": {"type": ["null", "string"]},
            "NUMBER_HEATED_ROOMS": {"type": ["null", "string"]},
            "NUMBER_OPEN_FIREPLACES": {"type": ["null", "string"]},
            "OSG_REFERENCE_NUMBER": {"type": ["null", "string"]},
            "PHOTO_SUPPLY": {"type": ["null", "string"]},
            "POSTCODE": {"type": ["null", "string"]},
            "POTENTIAL_ENERGY_EFFICIENCY": {"type": ["null", "string"]},
            "POTENTIAL_ENERGY_RATING": {"type": ["null", "string"]},
            "POTENTIAL_ENVIRONMENTAL_RATING": {"type": ["null", "string"]},
            "PROPERTY_TYPE": {"type": ["null", "string"]},
            "ROOF_DESCRIPTION": {"type": ["null", "string"]},
            "ROOF_ENERGY_EFF": {"type": ["null", "string"]},
            "ROOF_ENV_EFF": {"type": ["null", "string"]},
            "SECONDHEAT_DESCRIPTION": {"type": ["null", "string"]},
            "SHEATING_ENERGY_EFF": {"type": ["null", "string"]},
            "SHEATING_ENV_EFF": {"type": ["null", "string"]},
            "SOLAR_WATER_HEATING_FLAG": {"type": ["null", "string"]},
            "SPACE_HEATING_DEMAND": {"type": ["null", "string"]},
            "TENURE": {"type": ["null", "string"]},
            "TOTAL_FLOOR_AREA": {"type": ["null", "string"]},
            "TRANSACTION_TYPE": {"type": ["null", "string"]},
            "TYPE_OF_ASSESSMENT": {"type": ["null", "string"]},
            "UNHEATED_CORRIDOR_LENGTH": {"type": ["null", "string"]},
            "WALL_DESCRIPTION": {"type": ["null", "string"]},
            "WALL_ENERGY_EFF": {"type": ["null", "string"]},
            "WALL_ENV_EFF": {"type": ["null", "string"]},
            "WATER_HEATING_DEMAND": {"type": ["null", "string"]},
            "WINDOWS_DESCRIPTION": {"type": ["null", "string"]},
            "WINDOWS_ENERGY_EFF": {"type": ["null", "string"]},
            "WINDOWS_ENV_EFF": {"type": ["null", "string"]},
            "WIND_TURBINE_COUNT": {"type": ["null", "string"]},
            "SECONDHEATING_DESCRIPTION": {"type": ["null", "string"]},
            "SECONDHEATING_ENERGY_EFF": {"type": ["null", "string"]},
            "ENVIRONMENTAL_IMPACT_CURRENT": {"type": ["null", "string"]},
            "ENVIRONMENTAL_IMPACT_POTENTIAL": {"type": ["null", "string"]},
            "CERTIFICATE_NUMBER": {"type": ["null", "string"]},
            "RECOMMENDATIONS": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "CERTIFICATE_NUMBER": {"type": ["null", "string"]},
                        "IMPROVEMENT_DESCR_TEXT": {"type": ["null", "string"]},
                        "ENERGY_RATING_AFTER_IMPROVEMENT": {"type": ["null", "string"]},
                        "INDICATIVE_COST": {"type": ["null", "string"]},
                        "TYPICAL_SAVINGS": {"type": ["null", "string"]},
                    },
                },
            },
        }

        json_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": "",
            "properties": fields,
        }
        streams.append(
            AirbyteStream(
                name=stream_name,
                json_schema=json_schema,
                supported_sync_modes=["full_refresh"],
            ),
        )
        return AirbyteCatalog(streams=streams)

    def read(
        self,
        logger: AirbyteLogger,
        config: json,
        catalog: ConfiguredAirbyteCatalog,
        state: dict[str, any],
    ) -> Generator[AirbyteMessage, None, None]:
        """Returns a generator of the AirbyteMessages generated by reading the source with the given
        configuration, catalog, and state.

        :param logger: Logging object to display debug/info/error to the logs (logs will not be
            accessible via airbyte UI if they are not passed to this logger)
        :param config: Json object containing the configuration of this source, content of this json
            is as specified in the properties of the spec.yaml file
        :param catalog: The input catalog is a ConfiguredAirbyteCatalog which is almost the same as
            AirbyteCatalog returned by discover(), but in addition, it's been configured in the UI!

        For each particular stream and field, there may have been provided with extra modifications
        such as: filtering streams and/or columns out, renaming some entities, etc :param state:

        When a Airbyte reads data from a source, it might need to keep a checkpoint cursor to resume
        replication in the future from that saved checkpoint. This is the object that is provided
        with state from previous runs and avoid replicating the entire set of data every time.

        :return: A generator that produces a stream of AirbyteRecordMessage contained in
            AirbyteMessage object.
        """

        stream_name = "northern_ireland_epc"
        for rows in utils.main(logger=logger):
            if len(rows) > 0:
                logger.info(f"Yielding {len(rows)} AirbyteMessage records")

            for row in rows:
                yield AirbyteMessage(
                    type=Type.RECORD,
                    record=AirbyteRecordMessage(
                        stream=stream_name,
                        data=row,
                        emitted_at=int(datetime.now().timestamp()) * 1000,
                    ),
                )
