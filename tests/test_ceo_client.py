"""Tests for the CeoClient class."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from periodical_distiller.clients import CeoClient, ValidationError
from schemas.ceo_item import CeoItem


def make_ceo_response(articles, last_page=1, current_page=1):
    """Create a mock CEO API response."""
    response = MagicMock()
    response.is_success = True
    response.json.return_value = {
        "articles": articles,
        "pagination": {
            "first": 1,
            "last": last_page,
            "current": current_page,
        },
    }
    return response


@pytest.fixture
def ceo_config():
    """Configuration for CeoClient."""
    return {"base_url": "https://www.dailyprincetonian.com"}


@pytest.fixture
def mock_ceo_response(sample_ceo_record):
    """Create a mock response with CEO data."""
    return make_ceo_response([sample_ceo_record])


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

    return make_ceo_response(records)


class TestCeoClientFetch:
    """Tests for CeoClient.fetch() method."""

    def test_fetch_returns_ceo_items(self, ceo_config, sample_ceo_record):
        """fetch() returns a list of CeoItem objects."""
        client = CeoClient(ceo_config)

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = make_ceo_response([sample_ceo_record])
        client._client = mock_http_client

        items = client.fetch()

        assert len(items) == 1
        assert isinstance(items[0], CeoItem)
        assert items[0].id == "12345"
        assert items[0].headline == "Test Article Headline"

    def test_fetch_with_date_start_filters_articles(self, ceo_config, sample_ceo_record):
        """fetch() filters articles by date_start."""
        client = CeoClient(ceo_config)

        old_record = sample_ceo_record.copy()
        old_record["id"] = "111"
        old_record["ceo_id"] = "111"
        old_record["published_at"] = "2026-01-10 10:00:00"

        new_record = sample_ceo_record.copy()
        new_record["id"] = "222"
        new_record["ceo_id"] = "222"
        new_record["published_at"] = "2026-01-20 10:00:00"

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = make_ceo_response([new_record, old_record])
        client._client = mock_http_client

        items = client.fetch(date_start=date(2026, 1, 15))

        assert len(items) == 1
        assert items[0].id == "222"

    def test_fetch_with_date_end_filters_articles(self, ceo_config, sample_ceo_record):
        """fetch() filters articles by date_end."""
        client = CeoClient(ceo_config)

        old_record = sample_ceo_record.copy()
        old_record["id"] = "111"
        old_record["ceo_id"] = "111"
        old_record["published_at"] = "2026-01-10 10:00:00"

        new_record = sample_ceo_record.copy()
        new_record["id"] = "222"
        new_record["ceo_id"] = "222"
        new_record["published_at"] = "2026-01-20 10:00:00"

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = make_ceo_response([new_record, old_record])
        client._client = mock_http_client

        items = client.fetch(date_end=date(2026, 1, 15))

        assert len(items) == 1
        assert items[0].id == "111"

    def test_fetch_with_limit(self, ceo_config, mock_ceo_response_multiple):
        """fetch() respects limit parameter."""
        client = CeoClient(ceo_config)

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = mock_ceo_response_multiple
        client._client = mock_http_client

        items = client.fetch(limit=3)

        assert len(items) == 3

    def test_fetch_with_offset(self, ceo_config, sample_ceo_record):
        """fetch() calculates page from offset parameter."""
        client = CeoClient(ceo_config)

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = make_ceo_response([sample_ceo_record])
        client._client = mock_http_client

        # offset of 200 with default per_page of 100 should start at page 3
        client.fetch(offset=200)

        call_args = mock_http_client.request.call_args
        params = call_args.kwargs.get("params", {})
        assert params["page"] == 3

    def test_fetch_validate_false_returns_dicts(self, ceo_config, sample_ceo_record):
        """fetch(validate=False) returns raw dictionaries."""
        client = CeoClient(ceo_config)

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = make_ceo_response([sample_ceo_record])
        client._client = mock_http_client

        items = client.fetch(validate=False)

        assert len(items) == 1
        assert isinstance(items[0], dict)
        assert items[0]["id"] == "12345"

    def test_fetch_validation_error_on_invalid_data(self, ceo_config):
        """fetch() raises ValidationError when data fails schema validation."""
        client = CeoClient(ceo_config)

        # Missing required fields
        invalid_record = {"id": "12345", "published_at": "2026-01-15 10:00:00"}

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = make_ceo_response([invalid_record])
        client._client = mock_http_client

        with pytest.raises(ValidationError) as exc_info:
            client.fetch()

        assert "12345" in exc_info.value.message
        assert "failed validation" in exc_info.value.message
        assert len(exc_info.value.errors) > 0

    def test_fetch_empty_response(self, ceo_config):
        """fetch() returns empty list when no items found."""
        client = CeoClient(ceo_config)

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = make_ceo_response([])
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

        page1_response = make_ceo_response(page1_records, last_page=2, current_page=1)
        page2_response = make_ceo_response(page2_records, last_page=2, current_page=2)

        mock_http_client = MagicMock()
        mock_http_client.request.side_effect = [page1_response, page2_response]
        client._client = mock_http_client

        items = client.fetch()

        assert len(items) == 150
        assert mock_http_client.request.call_count == 2

    def test_pagination_stops_on_empty_page(self, ceo_config, sample_ceo_record):
        """fetch() stops paginating when an empty page is returned."""
        client = CeoClient(ceo_config)

        page1_response = make_ceo_response([sample_ceo_record], last_page=2)
        page2_response = make_ceo_response([], last_page=2)

        mock_http_client = MagicMock()
        mock_http_client.request.side_effect = [page1_response, page2_response]
        client._client = mock_http_client

        items = client.fetch()

        assert len(items) == 1

    def test_pagination_stops_at_last_page(self, ceo_config, sample_ceo_record):
        """fetch() stops paginating when reaching the last page."""
        client = CeoClient(ceo_config)

        page1_response = make_ceo_response([sample_ceo_record], last_page=1)

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = page1_response
        client._client = mock_http_client

        items = client.fetch()

        assert len(items) == 1
        assert mock_http_client.request.call_count == 1


class TestCeoClientConvenienceMethods:
    """Tests for CeoClient convenience methods."""

    def test_fetch_by_date(self, ceo_config, sample_ceo_record):
        """fetch_by_date() fetches articles for a specific date."""
        client = CeoClient(ceo_config)

        record = sample_ceo_record.copy()
        record["published_at"] = "2026-01-15 10:00:00"

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = make_ceo_response([record])
        client._client = mock_http_client

        items = client.fetch_by_date(date(2026, 1, 15))

        assert len(items) == 1

    def test_fetch_by_date_range(self, ceo_config, sample_ceo_record):
        """fetch_by_date_range() fetches articles within a date range."""
        client = CeoClient(ceo_config)

        record = sample_ceo_record.copy()
        record["published_at"] = "2026-01-15 10:00:00"

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = make_ceo_response([record])
        client._client = mock_http_client

        items = client.fetch_by_date_range(date(2026, 1, 10), date(2026, 1, 20))

        assert len(items) == 1

    def test_fetch_by_date_validate_false(self, ceo_config, sample_ceo_record):
        """fetch_by_date() respects validate=False."""
        client = CeoClient(ceo_config)

        record = sample_ceo_record.copy()
        record["published_at"] = "2026-01-15 10:00:00"

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = make_ceo_response([record])
        client._client = mock_http_client

        items = client.fetch_by_date(date(2026, 1, 15), validate=False)

        assert isinstance(items[0], dict)

    def test_fetch_by_date_range_validate_false(self, ceo_config, sample_ceo_record):
        """fetch_by_date_range() respects validate=False."""
        client = CeoClient(ceo_config)

        record = sample_ceo_record.copy()
        record["published_at"] = "2026-01-15 10:00:00"

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = make_ceo_response([record])
        client._client = mock_http_client

        items = client.fetch_by_date_range(date(2026, 1, 10), date(2026, 1, 20), validate=False)

        assert isinstance(items[0], dict)


class TestCeoClientDateMinSkip:
    """Tests that articles with unparseable dates are skipped, not halting pagination."""

    def test_none_published_at_is_skipped(self, ceo_config, sample_ceo_record, caplog):
        """Article with published_at=None is skipped with a warning."""
        client = CeoClient(ceo_config)

        valid1 = sample_ceo_record.copy()
        valid1["id"] = "111"
        valid1["ceo_id"] = "111"
        valid1["published_at"] = "2026-01-15 10:00:00"

        null_date = sample_ceo_record.copy()
        null_date["id"] = "999"
        null_date["ceo_id"] = "999"
        null_date["published_at"] = None

        valid2 = sample_ceo_record.copy()
        valid2["id"] = "222"
        valid2["ceo_id"] = "222"
        valid2["published_at"] = "2026-01-15 14:00:00"

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = make_ceo_response(
            [valid1, null_date, valid2]
        )
        client._client = mock_http_client

        import logging

        with caplog.at_level(logging.WARNING, logger="periodical_distiller.clients.ceo_client"):
            items = client.fetch(date_start=date(2026, 1, 15), validate=False)

        assert len(items) == 2
        assert {i["id"] for i in items} == {"111", "222"}
        assert any("999" in msg and "None" in msg for msg in caplog.messages)

    def test_invalid_published_at_is_skipped(self, ceo_config, sample_ceo_record, caplog):
        """Article with garbled published_at is skipped with a warning."""
        client = CeoClient(ceo_config)

        valid = sample_ceo_record.copy()
        valid["id"] = "111"
        valid["ceo_id"] = "111"
        valid["published_at"] = "2026-01-15 10:00:00"

        garbled = sample_ceo_record.copy()
        garbled["id"] = "888"
        garbled["ceo_id"] = "888"
        garbled["published_at"] = "not-a-date"

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = make_ceo_response([valid, garbled])
        client._client = mock_http_client

        import logging

        with caplog.at_level(logging.WARNING, logger="periodical_distiller.clients.ceo_client"):
            items = client.fetch(date_start=date(2026, 1, 15), validate=False)

        assert len(items) == 1
        assert items[0]["id"] == "111"
        assert any("888" in msg and "not-a-date" in msg for msg in caplog.messages)

    def test_pagination_continues_past_null_published_at(
        self, ceo_config, sample_ceo_record, caplog
    ):
        """Null published_at on page 1 does not halt pagination to page 2."""
        client = CeoClient(ceo_config)

        def make_record(record_id, published_at):
            r = sample_ceo_record.copy()
            r["id"] = record_id
            r["ceo_id"] = record_id
            r["published_at"] = published_at
            return r

        page1 = [
            make_record("p1a1", "2026-01-15 10:00:00"),
            make_record("p1a2", None),
            make_record("p1a3", "2026-01-15 12:00:00"),
        ]
        page2 = [
            make_record("p2a1", "2026-01-15 14:00:00"),
        ]

        mock_http_client = MagicMock()
        mock_http_client.request.side_effect = [
            make_ceo_response(page1, last_page=2, current_page=1),
            make_ceo_response(page2, last_page=2, current_page=2),
        ]
        client._client = mock_http_client

        import logging

        with caplog.at_level(logging.WARNING, logger="periodical_distiller.clients.ceo_client"):
            items = client.fetch(date_start=date(2026, 1, 15), validate=False)

        assert len(items) == 3
        assert {i["id"] for i in items} == {"p1a1", "p1a3", "p2a1"}
        assert mock_http_client.request.call_count == 2


class TestCeoClientContextManager:
    """Tests for CeoClient context manager usage."""

    def test_context_manager(self, ceo_config, sample_ceo_record):
        """CeoClient works as a context manager."""
        with CeoClient(ceo_config) as client:
            mock_http_client = MagicMock()
            mock_http_client.request.return_value = make_ceo_response([sample_ceo_record])
            client._client = mock_http_client

            items = client.fetch()
            assert len(items) == 1

        assert client._client is None
