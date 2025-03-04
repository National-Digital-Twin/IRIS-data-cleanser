import pytest
import pandas as pd
import logging
from unittest.mock import patch, MagicMock, mock_open
from io import BytesIO
import zipfile
import json

from source_epc_recommendations.utils import (
    requests_cached,
    fetch_recommendations_for_segment,
    main,
    MAX_PAGE_SIZE,
)


class TestUtils:
    """Test suite for the utils module."""

    @pytest.fixture
    def logger(self):
        """Create a mock logger for testing."""
        return MagicMock(spec=logging.Logger)

    @pytest.fixture
    def sample_csv_content(self):
        """Sample CSV content for testing."""
        return "LMK_KEY,IMPROVEMENT_ITEM,IMPROVEMENT_SUMMARY_TEXT\nABC123,1,Test summary\nDEF456,2,Test summary 2"

    @pytest.fixture
    def sample_df(self):
        """Sample DataFrame parsed from CSV content."""
        return pd.DataFrame({
            "LMK_KEY": ["ABC123", "DEF456"],
            "IMPROVEMENT_ITEM": [1, 2],
            "IMPROVEMENT_SUMMARY_TEXT": ["Test summary", "Test summary 2"]
        })

    def create_zip_response(self, content, status_code=200):
        """Helper to create a mock response with zipped content."""
        mock_response = MagicMock()
        mock_response.status_code = status_code

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('recommendations.csv', content)

        mock_response.content = zip_buffer.getvalue()
        return mock_response

    @patch('requests.Session')
    def test_requests_cached_success(self, mock_session, logger, sample_csv_content, sample_df):
        """Test requests_cached function with successful response."""
        mock_response = self.create_zip_response(sample_csv_content)

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        params = {"local-authority": "E06000046", "size": 1000}
        auth_key = "Basic test_key"
        result = requests_cached(params, logger, auth_key)

        assert isinstance(result, pd.DataFrame)
        pd.testing.assert_frame_equal(result, sample_df)

        # Verify API call
        mock_session_instance.get.assert_called_once()
        args, kwargs = mock_session_instance.get.call_args
        assert args[0] == "https://epc.opendatacommunities.org/api/v1/domestic/search"
        assert kwargs["params"] == params
        assert kwargs["headers"]["Authorization"] == auth_key

    @patch('requests.Session')
    def test_requests_cached_no_recommendations(self, mock_session, logger):
        """Test requests_cached when no recommendations.csv file exists in the response."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            zf.writestr('other_file.csv', "some content")

        mock_response.content = zip_buffer.getvalue()

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        params = {"local-authority": "E06000046", "size": 1000}
        result = requests_cached(params, logger)

        assert result is None

    @patch('requests.Session')
    def test_requests_cached_error_500(self, mock_session, logger):
        """Test requests_cached with a 500 error response."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        params = {"local-authority": "E06000046", "size": 1000}

        with pytest.raises(RuntimeError) as excinfo:
            requests_cached(params, logger)

        assert "Encountered error 500" in str(excinfo.value)

        logger.error.assert_called_once()

    @patch('requests.Session')
    def test_requests_cached_other_error(self, mock_session, logger):
        """Test requests_cached with a non-500 error response."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_session_instance = MagicMock()
        mock_session_instance.get.return_value = mock_response
        mock_session.return_value = mock_session_instance

        params = {"local-authority": "E06000046", "size": 1000}

        with pytest.raises(RuntimeError) as excinfo:
            requests_cached(params, logger)

        assert "Encountered error 401" in str(excinfo.value)
        assert "params=" in str(excinfo.value)

        logger.error.assert_called_once()

    @patch('source_epc_recommendations.utils.requests_cached')
    def test_fetch_recommendations_for_segment_single_page(self, mock_requests_cached, logger, sample_df):
        """Test fetch_recommendations_for_segment with a single page of results."""
        mock_requests_cached.return_value = sample_df

        result = fetch_recommendations_for_segment(
            local_authority="E06000046",
            year=2020,
            month=5,
            energy_band="a",
            logger=logger,
        )

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

        mock_requests_cached.assert_called_once()
        _, kwargs = mock_requests_cached.call_args
        params = kwargs["params"]
        assert params["local-authority"] == "E06000046"
        assert params["from-year"] == 2020
        assert params["to-year"] == 2020
        assert params["from-month"] == 5
        assert params["to-month"] == 5
        assert params["energy-band"] == "a"
        assert params["size"] == MAX_PAGE_SIZE
        assert params["from"] == 0

    @patch('source_epc_recommendations.utils.requests_cached')
    def test_fetch_recommendations_for_segment_multiple_pages(self, mock_requests_cached, logger):
        """Test fetch_recommendations_for_segment with multiple pages of results."""
        page1 = pd.DataFrame({
            "LMK_KEY": [f"KEY{i}" for i in range(MAX_PAGE_SIZE)],
            "IMPROVEMENT_ITEM": [i for i in range(MAX_PAGE_SIZE)]
        })

        page2 = pd.DataFrame({
            "LMK_KEY": [f"KEY{i+MAX_PAGE_SIZE}" for i in range(50)],  # Smaller than MAX_PAGE_SIZE
            "IMPROVEMENT_ITEM": [i+MAX_PAGE_SIZE for i in range(50)]
        })

        mock_requests_cached.side_effect = [page1, page2]

        result = fetch_recommendations_for_segment(
            local_authority="E06000046",
            year=2020,
            month=5,
            energy_band="a",
            logger=logger,
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == MAX_PAGE_SIZE + 50

        assert mock_requests_cached.call_count == 2

        first_call_args = mock_requests_cached.call_args_list[0][1]["params"]
        assert first_call_args["from"] == 0

        second_call_args = mock_requests_cached.call_args_list[1][1]["params"]
        assert second_call_args["from"] == MAX_PAGE_SIZE

    @patch('source_epc_recommendations.utils.requests_cached')
    def test_fetch_recommendations_for_segment_no_results(self, mock_requests_cached, logger):
        """Test fetch_recommendations_for_segment when no results are returned."""
        mock_requests_cached.return_value = None

        result = fetch_recommendations_for_segment(
            local_authority="E06000046",
            year=2020,
            month=5,
            energy_band="a",
            logger=logger,
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0  # Empty DataFrame

        mock_requests_cached.assert_called_once()

    @patch('source_epc_recommendations.utils.fetch_recommendations_for_segment')
    def test_main_function(self, mock_fetch, logger, sample_df):
        """Test the main function with a simplified set of parameters."""
        mock_fetch.return_value = sample_df

        result = main(
            local_authority_list=["E06000046"],
            start_year=2023,
            end_year=2023,
            auth_key="test_key",
            logger=logger
        )

        assert isinstance(result, pd.DataFrame)

        # For a single local authority, single year, 12 months, 7 energy bands (a-g),
        # we expect 12*7=84 calls to fetch_recommendations_for_segment
        assert mock_fetch.call_count == 84

        # Verify one of the calls to fetch_recommendations_for_segment
        first_call_args = mock_fetch.call_args_list[0]
        assert first_call_args[0][0] == "E06000046"
        assert first_call_args[0][1] == 2023
        assert first_call_args[0][2] == 1
        assert first_call_args[0][3] == "a"

        logger.info.assert_any_call("Getting data for 2023-1 for local authority E06000046")

        final_call_message = logger.info.call_args_list[-1][0][0]
        assert "rows retrieved from the EPC API" in final_call_message