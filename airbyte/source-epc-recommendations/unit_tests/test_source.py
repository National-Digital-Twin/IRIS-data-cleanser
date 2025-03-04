import json
import pytest
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd

from airbyte_cdk.models import (
    AirbyteConnectionStatus,
    AirbyteRecordMessage,
    AirbyteMessage,
    Status,
    Type,
    SyncMode
)

from source_epc_recommendations.source import SourceEpcRecommendations


class TestSourceEpcRecommendations:
    """Test suite for the SourceEpcRecommendations class."""

    @pytest.fixture
    def source(self):
        """Create a source instance for testing."""
        return SourceEpcRecommendations()

    @pytest.fixture
    def logger(self):
        """Create a mock logger for testing."""
        return MagicMock()

    @pytest.fixture
    def config(self):
        """Create a sample configuration for testing."""
        return {
            "auth_key": "Basic test_auth_key",
            "local_authority_list": "E06000046,E06000011",
            "start_year": 2020,
            "end_year": 2022,
        }

    @pytest.fixture
    def catalog(self):
        """Create a mock catalog for testing."""
        return MagicMock()

    @pytest.fixture
    def state(self):
        """Create a mock state for testing."""
        return {}

    @pytest.fixture
    def sample_recommendations_data(self):
        """Create sample recommendations data for testing."""
        return pd.DataFrame({
            "LMK_KEY": ["ABC123", "DEF456"],
            "IMPROVEMENT_ITEM": [1, 2],
            "IMPROVEMENT_SUMMARY_TEXT": ["Improve insulation", "Install solar panels"],
            "IMPROVEMENT_DESCR_TEXT": ["Detailed description 1", "Detailed description 2"],
            "IMPROVEMENT_ID": [101, 102],
            "IMPROVEMENT_ID_TEXT": ["ID Text 1", "ID Text 2"],
            "INDICATIVE_COST": ["£100-£350", "£3000-£5000"],
        })

    @patch('requests.Session')
    def test_check_success(self, mock_session, source, logger, config):
        """Test check method with successful response."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        result = source.check(logger, config)

        assert isinstance(result, AirbyteConnectionStatus)
        assert result.status == Status.SUCCEEDED

        # Verify API call
        mock_session_instance.get.assert_called_once()
        args, kwargs = mock_session_instance.get.call_args
        assert args[0] == "https://epc.opendatacommunities.org/api/v1/domestic/search"
        assert kwargs["headers"]["Authorization"] == config["auth_key"]

    @patch('requests.Session')
    def test_check_failure(self, mock_session, source, logger, config):
        """Test check method with failed response."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        result = source.check(logger, config)

        assert isinstance(result, AirbyteConnectionStatus)
        assert result.status == Status.FAILED
        assert "Authorization failed" in result.message

    @patch('requests.Session')
    def test_check_exception(self, mock_session, source, logger, config):
        """Test check method when an exception occurs."""
        mock_session_instance = MagicMock()
        mock_session_instance.get.side_effect = Exception("Test exception")
        mock_session.return_value = mock_session_instance

        result = source.check(logger, config)

        assert isinstance(result, AirbyteConnectionStatus)
        assert result.status == Status.FAILED
        assert "An exception occurred" in result.message
        assert "Test exception" in result.message

    def test_discover(self, source, logger, config):
        """Test discover method returns correct catalog."""
        catalog = source.discover(logger, config)

        assert len(catalog.streams) == 1
        stream = catalog.streams[0]
        assert stream.name == "recommendations"

        schema = stream.json_schema
        assert schema["type"] == "object"
        assert "LMK_KEY" in schema["properties"]
        assert "IMPROVEMENT_ITEM" in schema["properties"]
        assert "IMPROVEMENT_SUMMARY_TEXT" in schema["properties"]

        assert SyncMode.full_refresh in stream.supported_sync_modes

    @patch('source_epc_recommendations.utils.main')
    def test_read(self, mock_utils_main, source, logger, config, catalog, state, sample_recommendations_data):
        """Test read method yields correct messages."""
        mock_utils_main.return_value = sample_recommendations_data
        messages = list(source.read(logger, config, catalog, state))
        assert len(messages) == 2  # Two records in our sample data

        for i, message in enumerate(messages):
            assert isinstance(message, AirbyteMessage)
            assert message.type == Type.RECORD

            record = message.record
            assert isinstance(record, AirbyteRecordMessage)
            assert record.stream == "recommendations"

            if i == 0:
                assert record.data["LMK_KEY"] == "ABC123"
                assert record.data["IMPROVEMENT_ITEM"] == 1
                assert record.data["IMPROVEMENT_SUMMARY_TEXT"] == "Improve insulation"
            else:
                assert record.data["LMK_KEY"] == "DEF456"
                assert record.data["IMPROVEMENT_ITEM"] == 2
                assert record.data["IMPROVEMENT_SUMMARY_TEXT"] == "Install solar panels"

        # Verify utils.main was called with correct parameters
        mock_utils_main.assert_called_once()
        _, kwargs = mock_utils_main.call_args
        assert kwargs["local_authority_list"] == config["local_authority_list"].split(",")
        assert kwargs["start_year"] == config["start_year"]
        assert kwargs["end_year"] == config["end_year"]
        assert kwargs["auth_key"] == config["auth_key"]
        assert kwargs["logger"] == logger