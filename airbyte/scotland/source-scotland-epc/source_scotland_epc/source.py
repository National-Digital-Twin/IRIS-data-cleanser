"""Copyright (c) 2023 Airbyte, Inc., all rights reserved."""

import json
from collections.abc import Generator
from datetime import datetime

import numpy as np
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

from . import utils


class SourceScotlandEpc(Source):
    def spec(self, logger: AirbyteLogger) -> ConnectorSpecification:
        """Returns the spec for this connector."""
        return ConnectorSpecification(
            documentationUrl="https://docs.airbyte.com/integrations/sources/scotland-epc-certificates",
            changelogUrl="https://docs.airbyte.com/integrations/sources/scotland-epc-certificates",
            supportsIncremental=True,
            supported_destination_sync_modes=[DestinationSyncMode.append],
            connectionSpecification={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "Scotland EPC Certificates Spec",
                "type": "object",
                "required": ["property_type", "data_type"],
                "properties": {
                    "property_type": {
                        "type": "string",
                        "enum": ["domestic", "non-domestic"],
                        "default": "domestic",
                        "description": "The type of property to fetch EPC certificates for.",
                    },
                    "data_type": {
                        "type": "string",
                        "enum": ["certificates", "recommendations"],
                        "default": "certificates",
                        "description": "Fetch certificates or recommendations.",
                    },
                },
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
            property_type = config["property_type"]
            _, status = utils.get_download_url(property_type=property_type)
            if status == 200:
                return AirbyteConnectionStatus(status=Status.SUCCEEDED)

            return AirbyteConnectionStatus(
                status=Status.FAILED,
                message=f"Authorization failed with status {status}",
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

        data_type = config["data_type"]  # either certificates or recommendations
        property_type = config["property_type"]  # either domestic or non-domestic
        stream_name = f"scotland_{data_type}_{property_type.replace('-', '_')}"
        json_schema = self.get_json_schema(data_type, property_type)
        streams.append(
            AirbyteStream(
                name=stream_name,
                json_schema=json_schema,
                supported_sync_modes=["full_refresh"],
                source_defined_cursor=True,
                default_cursor_field=["LODGEMENT_DATE"],
            ),
        )
        return AirbyteCatalog(streams=streams)

    def get_json_schema(self, data_type, property_type):
        """Returns the JSON schema for the given data type and property type."""
        # Define the common fields
        certificates_common_fields = {
            "BUILDING_REFERENCE_NUMBER": {"type": ["null", "string"]},
            "OSG_REFERENCE_NUMBER": {"type": ["null", "string"]},
            "ADDRESS1": {"type": ["null", "string"]},
            "ADDRESS2": {"type": ["null", "string"]},
            "POSTCODE": {"type": ["null", "string"]},
            "INSPECTION_DATE": {"type": ["null", "string"]},
            "LODGEMENT_DATE": {"type": ["null", "string"]},
            "PROPERTY_TYPE": {"type": ["null", "string"]},
            "DATA_ZONE": {"type": ["null", "string"]},
            "DATA_ZONE_2011": {"type": ["null", "string"]},
            "CONSTITUENCY": {"type": ["null", "string"]},
            "CONSTITUENCY_LABEL": {"type": ["null", "string"]},
            "TRANSACTION_TYPE": {"type": ["null", "string"]},
            "CREATED_AT": {"type": ["null", "string"]},
            "DOMESTIC": {"type": ["null", "string"]},
        }

        # Define the domestic-specific fields
        certificates_domestic_fields = {
            "ADDRESS3": {"type": ["null", "string"]},
            "TYPE_OF_ASSESSMENT": {"type": ["null", "string"]},
            "TOTAL_FLOOR_AREA": {"type": ["null", "string"]},
            "ENERGY_CONSUMPTION_CURRENT": {"type": ["null", "string"]},
            "3_YR_ENERGY_COST_CURRENT": {"type": ["null", "string"]},
            "3_YR_ENERGY_SAVINGS_POTENTIAL": {"type": ["null", "string"]},
            "CURRENT_ENERGY_EFFICIENCY": {"type": ["null", "string"]},
            "CURRENT_ENERGY_RATING": {"type": ["null", "string"]},
            "POTENTIAL_ENERGY_EFFICIENCY": {"type": ["null", "string"]},
            "POTENTIAL_ENERGY_RATING": {"type": ["null", "string"]},
            "ENVIRONMENT_IMPACT_CURRENT": {"type": ["null", "string"]},
            "CURRENT_ENVIRONMENTAL_RATING": {"type": ["null", "string"]},
            "ENVIRONMENT_IMPACT_POTENTIAL": {"type": ["null", "string"]},
            "POTENTIAL_ENVIRONMENTAL_RATING": {"type": ["null", "string"]},
            "CO2_EMISS_CURR_PER_FLOOR_AREA": {"type": ["null", "string"]},
            "IMPROVEMENTS": {"type": ["null", "string"]},
            "WALL_DESCRIPTION": {"type": ["null", "string"]},
            "WALLS_ENERGY_EFF": {"type": ["null", "string"]},
            "WALLS_ENV_EFF": {"type": ["null", "string"]},
            "ROOF_DESCRIPTION": {"type": ["null", "string"]},
            "ROOF_ENERGY_EFF": {"type": ["null", "string"]},
            "ROOF_ENV_EFF": {"type": ["null", "string"]},
            "FLOOR_DESCRIPTION": {"type": ["null", "string"]},
            "FLOOR_ENERGY_EFF": {"type": ["null", "string"]},
            "FLOOR_ENV_EFF": {"type": ["null", "string"]},
            "WINDOWS_DESCRIPTION": {"type": ["null", "string"]},
            "WINDOWS_ENERGY_EFF": {"type": ["null", "string"]},
            "WINDOWS_ENV_EFF": {"type": ["null", "string"]},
            "MAINHEAT_DESCRIPTION": {"type": ["null", "string"]},
            "MAINHEAT_ENERGY_EFF": {"type": ["null", "string"]},
            "MAINHEAT_ENV_EFF": {"type": ["null", "string"]},
            "MAINHEATCONT_DESCRIPTION": {"type": ["null", "string"]},
            "MAINHEATC_ENERGY_EFF": {"type": ["null", "string"]},
            "MAINHEATC_ENV_EFF": {"type": ["null", "string"]},
            "SECONDHEAT_DESCRIPTION": {"type": ["null", "string"]},
            "SHEATING_ENERGY_EFF": {"type": ["null", "string"]},
            "SHEATING_ENV_EFF": {"type": ["null", "string"]},
            "HOTWATER_DESCRIPTION": {"type": ["null", "string"]},
            "HOT_WATER_ENERGY_EFF": {"type": ["null", "string"]},
            "HOT_WATER_ENV_EFF": {"type": ["null", "string"]},
            "LIGHTING_DESCRIPTION": {"type": ["null", "string"]},
            "LIGHTING_ENERGY_EFF": {"type": ["null", "string"]},
            "LIGHTING_ENV_EFF": {"type": ["null", "string"]},
            "AIR_TIGHTNESS_DESCRIPTION": {"type": ["null", "string"]},
            "AIR_TIGHTNESS_ENERGY_EFF": {"type": ["null", "string"]},
            "AIR_TIGHTNESS_ENV_EFF": {"type": ["null", "string"]},
            "CO2_EMISSIONS_CURRENT": {"type": ["null", "string"]},
            "CO2_EMISSIONS_POTENTIAL": {"type": ["null", "string"]},
            "HEATING_COST_CURRENT": {"type": ["null", "string"]},
            "HEATING_COST_POTENTIAL": {"type": ["null", "string"]},
            "HOT_WATER_COST_CURRENT": {"type": ["null", "string"]},
            "HOT_WATER_COST_POTENTIAL": {"type": ["null", "string"]},
            "LIGHTING_COST_CURRENT": {"type": ["null", "string"]},
            "LIGHTING_COST_POTENTIAL": {"type": ["null", "string"]},
            "ALTERNATIVE_IMPROVEMENTS": {"type": ["null", "string"]},
            "LZC_ENERGY_SOURCES": {"type": ["null", "string"]},
            "SPACE_HEATING_DEMAND": {"type": ["null", "string"]},
            "WATER_HEATING_DEMAND": {"type": ["null", "string"]},
            "IMPACT_LOFT_INSULATION": {"type": ["null", "string"]},
            "IMPACT_CAVITY_WALL_INSULATION": {"type": ["null", "string"]},
            "IMPACT_SOLID_WALL_INSULATION": {"type": ["null", "string"]},
            "ADDENDUM_": {"type": ["null", "string"]},
            "CONSTRUCTION_AGE_BAND": {"type": ["null", "string"]},
            "FLOOR_HEIGHT": {"type": ["null", "string"]},
            "ENERGY_CONSUMPTION_POTENTIAL": {"type": ["null", "string"]},
            "EXTENSION_COUNT": {"type": ["null", "string"]},
            "FIXED_LIGHTING_OUTLETS_COUNT": {"type": ["null", "string"]},
            "LOW_ENERGY_FIXED_LIGHT_COUNT": {"type": ["null", "string"]},
            "LOW_ENERGY_LIGHTING": {"type": ["null", "string"]},
            "FLOOR_LEVEL": {"type": ["null", "string"]},
            "FLAT_TOP_STOREY": {"type": ["null", "string"]},
            "GLAZED_AREA": {"type": ["null", "string"]},
            "NUMBER_HABITABLE_ROOMS": {"type": ["null", "string"]},
            "HEAT_LOSS_CORRIDOOR": {"type": ["null", "string"]},
            "NUMBER_HEATED_ROOMS": {"type": ["null", "string"]},
            "LOCAL_AUTHORITY_LABEL": {"type": ["null", "string"]},
            "MAINS_GAS_FLAG": {"type": ["null", "string"]},
            "MAIN_HEATING_CATEGORY": {"type": ["null", "string"]},
            "MAIN_FUEL": {"type": ["null", "string"]},
            "MAIN_HEATING_CONTROLS": {"type": ["null", "string"]},
            "MECHANICAL_VENTILATION": {"type": ["null", "string"]},
            "ENERGY_TARIFF": {"type": ["null", "string"]},
            "MULTI_GLAZE_PROPORTION": {"type": ["null", "string"]},
            "GLAZED_TYPE": {"type": ["null", "string"]},
            "NUMBER_OPEN_FIREPLACES": {"type": ["null", "string"]},
            "PHOTO_SUPPLY": {"type": ["null", "string"]},
            "SOLAR_WATER_HEATING_FLAG": {"type": ["null", "string"]},
            "TENURE": {"type": ["null", "string"]},
            "UNHEATED_CORRIDOR_LENGTH": {"type": ["null", "string"]},
            "WIND_TURBINE_COUNT": {"type": ["null", "string"]},
            "BUILT_FORM": {"type": ["null", "string"]},
        }

        # Define the non-domestic-specific fields
        certificates_non_domestic_fields = {
            "POST_TOWN": {"type": ["null", "string"]},
            "PROPERTY_TYPE_SHORT": {"type": ["null", "string"]},
            "FLOOR_AREA": {"type": ["null", "string"]},
            "CURRENT_ENERGY_PERFORMANCE_RATING": {"type": ["null", "string"]},
            "CURRENT_ENERGY_PERFORMANCE_BAND": {"type": ["null", "string"]},
            "POTENTIAL_ENERGY_PERFORMANCE_RATING": {"type": ["null", "string"]},
            "POTENTIAL_ENERGY_PERFORMANCE_BAND": {"type": ["null", "string"]},
            "NEW_BUILD_ENERGY_PERFORMANCE_RATING": {"type": ["null", "string"]},
            "NEW_BUILD_ENERGY_PERFORMANCE_BAND": {"type": ["null", "string"]},
            "MEETS_2002_STANDARD": {"type": ["null", "string"]},
            "ASSET_RATING": {"type": ["null", "string"]},
            "ASSET_RATING_BAND": {"type": ["null", "string"]},
            "BUILDING_EMISSIONS": {"type": ["null", "string"]},
            "RENEWABLE_SOURCES": {"type": ["null", "string"]},
            "ELECTRICITY_SOURCE": {"type": ["null", "string"]},
            "MAIN_HEATING_FUEL": {"type": ["null", "string"]},
            "BUILDING_ENVIRONMENT": {"type": ["null", "string"]},
            "PRIMARY_ENERGY_VALUE": {"type": ["null", "string"]},
            "APPROXIMATE_ENERGY_USE": {"type": ["null", "string"]},
            "IMPROVEMENT_RECOMMENDATIONS": {"type": ["null", "string"]},
            "LOCAL_AUTHORITY": {"type": ["null", "string"]},
            "TARGET_EMISSIONS": {"type": ["null", "string"]},
        }

        recommendations_common_fields = {
            "BUILDING_REFERENCE_NUMBER": {"type": ["null", "string"]},
            "IMPROVEMENT_DESCR_TEXT": {"type": ["null", "string"]},
        }

        recommendations_domestic_fields = {
            "INDICATIVE_COST": {"type": ["null", "string"]},
            "TYPICAL_SAVING": {"type": ["null", "string"]},
            "ENERGY_RATING_AFTER_IMPROVEMENT": {"type": ["null", "string"]},
            "ENVIRONMENTAL_RATING_AFTER_IMPROVEMENT": {"type": ["null", "string"]},
            "GREEN_DEAL_ELIGIBLE": {"type": ["null", "string"]},
        }

        recommendations_non_domestic_fields = {
            "CODE": {"type": ["null", "string"]},
            "C02_IMPACT": {"type": ["null", "string"]},
            "PAYBACK_TYPE": {"type": ["null", "string"]},
        }

        # Combine the fields based on the property type
        if data_type == "certificates":
            if property_type == "domestic":
                fields = {**certificates_common_fields, **certificates_domestic_fields}
            elif property_type == "non-domestic":
                fields = {**certificates_common_fields, **certificates_non_domestic_fields}
        elif data_type == "recommendations":
            if property_type == "domestic":
                fields = {**recommendations_common_fields, **recommendations_domestic_fields}
            elif property_type == "non-domestic":
                fields = {**recommendations_common_fields, **recommendations_non_domestic_fields}
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": "",
            "properties": fields,
        }

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

        property_type = config["property_type"]
        data_type = config["data_type"]
        stream_name = f"scotland_{data_type}_{property_type.replace('-', '_')}"

        epc_certificates, epc_recommendations = utils.main(
            property_type=property_type,
            logger=logger,
        )

        logger.info(f"Yielding {len(epc_certificates)} AirbyteMessage records")
        if data_type == "certificates":
            dataframe = epc_certificates
        elif data_type == "recommendations":
            dataframe = epc_recommendations
        # Emit to Airbyte
        for row in dataframe.replace({np.nan: None}).to_dict(orient="records"):
            yield AirbyteMessage(
                type=Type.RECORD,
                record=AirbyteRecordMessage(
                    stream=stream_name,
                    data=row,
                    emitted_at=int(datetime.now().timestamp()) * 1000,
                ),
            )
