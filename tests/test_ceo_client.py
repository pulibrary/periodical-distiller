"""Tests for the CeoClient class."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from periodical_distiller.clients import CeoClient, ValidationError
from schemas.ceo_item import CeoItem


@pytest.fixture
def ceo_config():
    """Configuration for CeoClient."""
    return {"base_url": "https://www.dailyprincetonian.com"}


@pytest.fixture
def mock_ceo_response(sample_ceo_record):
    """Create a mock response with CEO data."""
    response = MagicMock()
    response.is_success = True
    response.json.return_value = [sample_ceo_record]
    return response


@pytest.fixture
def mock_ceo_response_multiple(sample_ceo_record):
    """Create a mock response with multiple CEO records."""
    records = []
    for i in range(5):
        record = sample_ceo_record.copy()
        record["id"] = str(12345 + i)
        record["uuid"] = f"abc-123-def-{i}"
        record["ceo_id"] = str(12345 + i)
        records.append(record)

    response = MagicMock()
    response.is_success = True
    response.json.return_value = records
    return response


class TestCeoClientFetch:
    """Tests for CeoClient.fetch() method."""

    def test_fetch_returns_ceo_items(self, ceo_config, sample_ceo_record):
        """fetch() returns a list of CeoItem objects."""
        client = CeoClient(ceo_config)

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = [sample_ceo_record]

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        items = client.fetch()

        assert len(items) == 1
        assert isinstance(items[0], CeoItem)
        assert items[0].id == "12345"
        assert items[0].headline == "Test Article Headline"

    def test_fetch_with_date_start(self, ceo_config, sample_ceo_record):
        """fetch() passes date_start parameter correctly."""
        client = CeoClient(ceo_config)

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = [sample_ceo_record]

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        client.fetch(date_start=date(2026, 1, 15))

        call_args = mock_http_client.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params["start_date"] == "2026-01-15"

    def test_fetch_with_date_end(self, ceo_config, sample_ceo_record):
        """fetch() passes date_end parameter correctly."""
        client = CeoClient(ceo_config)

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = [sample_ceo_record]

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        client.fetch(date_end=date(2026, 1, 20))

        call_args = mock_http_client.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params["end_date"] == "2026-01-20"

    def test_fetch_with_limit(self, ceo_config, mock_ceo_response_multiple):
        """fetch() respects limit parameter."""
        client = CeoClient(ceo_config)

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_ceo_response_multiple
        client._client = mock_http_client

        items = client.fetch(limit=3)

        assert len(items) == 3

    def test_fetch_with_offset(self, ceo_config, sample_ceo_record):
        """fetch() passes offset parameter correctly."""
        client = CeoClient(ceo_config)

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = [sample_ceo_record]

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        client.fetch(offset=10)

        call_args = mock_http_client.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params["offset"] == 10

    def test_fetch_validate_false_returns_dicts(self, ceo_config, sample_ceo_record):
        """fetch(validate=False) returns raw dictionaries."""
        client = CeoClient(ceo_config)

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = [sample_ceo_record]

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        items = client.fetch(validate=False)

        assert len(items) == 1
        assert isinstance(items[0], dict)
        assert items[0]["id"] == "12345"

    def test_fetch_validation_error_on_invalid_data(self, ceo_config):
        """fetch() raises ValidationError when data fails schema validation."""
        client = CeoClient(ceo_config)

        invalid_record = {"id": "12345"}  # Missing required fields

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = [invalid_record]

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        with pytest.raises(ValidationError) as exc_info:
            client.fetch()

        assert "12345" in exc_info.value.message
        assert "failed validation" in exc_info.value.message
        assert len(exc_info.value.errors) > 0

    def test_fetch_empty_response(self, ceo_config):
        """fetch() returns empty list when no items found."""
        client = CeoClient(ceo_config)

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = []

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        items = client.fetch()

        assert items == []


class TestCeoClientPagination:
    """Tests for CeoClient pagination handling."""

    def test_pagination_fetches_all_pages(self, ceo_config, sample_ceo_record):
        """fetch() automatically handles pagination to get all items."""
        client = CeoClient(ceo_config)

        page1_records = []
        for i in range(100):
            record = sample_ceo_record.copy()
            record["id"] = str(i)
            record["uuid"] = f"uuid-{i}"
            record["ceo_id"] = str(i)
            page1_records.append(record)

        page2_records = []
        for i in range(50):
            record = sample_ceo_record.copy()
            record["id"] = str(100 + i)
            record["uuid"] = f"uuid-{100 + i}"
            record["ceo_id"] = str(100 + i)
            page2_records.append(record)

        page1_response = MagicMock()
        page1_response.is_success = True
        page1_response.json.return_value = page1_records

        page2_response = MagicMock()
        page2_response.is_success = True
        page2_response.json.return_value = page2_records

        mock_http_client = MagicMock()
        mock_http_client.request.side_effect = [page1_response, page2_response]
        client._client = mock_http_client

        items = client.fetch()

        assert len(items) == 150
        assert mock_http_client.request.call_count == 2

    def test_pagination_stops_on_empty_page(self, ceo_config, sample_ceo_record):
        """fetch() stops paginating when an empty page is returned."""
        client = CeoClient(ceo_config)

        page1_response = MagicMock()
        page1_response.is_success = True
        page1_response.json.return_value = [sample_ceo_record]

        page2_response = MagicMock()
        page2_response.is_success = True
        page2_response.json.return_value = []

        mock_http_client = MagicMock()
        mock_http_client.request.side_effect = [page1_response, page2_response]
        client._client = mock_http_client

        items = client.fetch()

        assert len(items) == 1


class TestCeoClientConvenienceMethods:
    """Tests for CeoClient convenience methods."""

    def test_fetch_by_date(self, ceo_config, sample_ceo_record):
        """fetch_by_date() fetches articles for a specific date."""
        client = CeoClient(ceo_config)

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = [sample_ceo_record]

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        items = client.fetch_by_date(date(2026, 1, 15))

        assert len(items) == 1
        call_args = mock_http_client.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params["start_date"] == "2026-01-15"
        assert params["end_date"] == "2026-01-15"

    def test_fetch_by_date_range(self, ceo_config, sample_ceo_record):
        """fetch_by_date_range() fetches articles within a date range."""
        client = CeoClient(ceo_config)

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = [sample_ceo_record]

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        items = client.fetch_by_date_range(date(2026, 1, 10), date(2026, 1, 20))

        assert len(items) == 1
        call_args = mock_http_client.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params["start_date"] == "2026-01-10"
        assert params["end_date"] == "2026-01-20"

    def test_fetch_by_date_validate_false(self, ceo_config, sample_ceo_record):
        """fetch_by_date() respects validate=False."""
        client = CeoClient(ceo_config)

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = [sample_ceo_record]

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        items = client.fetch_by_date(date(2026, 1, 15), validate=False)

        assert isinstance(items[0], dict)

    def test_fetch_by_date_range_validate_false(self, ceo_config, sample_ceo_record):
        """fetch_by_date_range() respects validate=False."""
        client = CeoClient(ceo_config)

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = [sample_ceo_record]

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_response
        client._client = mock_http_client

        items = client.fetch_by_date_range(date(2026, 1, 10), date(2026, 1, 20), validate=False)

        assert isinstance(items[0], dict)


class TestCeoClientContextManager:
    """Tests for CeoClient context manager usage."""

    def test_context_manager(self, ceo_config, sample_ceo_record):
        """CeoClient works as a context manager."""
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = [sample_ceo_record]

        with CeoClient(ceo_config) as client:
            mock_http_client = MagicMock()
            mock_http_client.request.return_value = mock_response
            client._client = mock_http_client

            items = client.fetch()
            assert len(items) == 1

        assert client._client is None
