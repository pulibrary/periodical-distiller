"""Tests for the PIPAggregator class."""

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from periodical_distiller.aggregators import MediaDownloader, PIPAggregator
from periodical_distiller.clients import CeoClient
from schemas.ceo_item import CeoItem, CeoMedia
from schemas.pip import PIPManifest, PIPMedia


@pytest.fixture
def mock_ceo_client(ceo_config):
    """Create a mock CeoClient."""
    client = CeoClient(ceo_config)
    client._client = MagicMock()
    return client


@pytest.fixture
def ceo_config():
    """Configuration for CeoClient."""
    return {"base_url": "https://www.dailyprincetonian.com"}


@pytest.fixture
def sample_ceo_items(sample_ceo_record):
    """Create sample CeoItem objects for testing."""
    items = []
    for i in range(3):
        record = sample_ceo_record.copy()
        record["id"] = str(12345 + i)
        record["ceo_id"] = str(12345 + i)
        record["uuid"] = f"uuid-{i}"
        record["headline"] = f"Test Article {i + 1}"
        items.append(CeoItem.model_validate(record))
    return items


@pytest.fixture
def sample_ceo_media():
    """Create a sample CeoMedia object for testing."""
    return CeoMedia(
        id="m1",
        uuid="media-uuid-123",
        attachment_uuid="attach-uuid-456",
        base_name="test-image",
        extension="jpg",
        preview_extension="jpg",
        status="published",
        weight="0",
        hits="0",
        transcoded="0",
        created_at="2026-01-15 10:00:00",
        modified_at="2026-01-15 12:00:00",
        ceo_id="m1",
    )


@pytest.fixture
def sample_ceo_items_with_media(sample_ceo_record, sample_ceo_media):
    """Create sample CeoItem objects with dominant media."""
    items = []
    for i in range(3):
        record = sample_ceo_record.copy()
        record["id"] = str(12345 + i)
        record["ceo_id"] = str(12345 + i)
        record["uuid"] = f"uuid-{i}"
        record["headline"] = f"Test Article {i + 1}"
        media = sample_ceo_media.model_dump()
        media["base_name"] = f"image-{i}"
        record["dominantMedia"] = media
        items.append(CeoItem.model_validate(record))
    return items


@pytest.fixture
def mock_media_downloader():
    """Create a mock MediaDownloader."""
    downloader = MagicMock(spec=MediaDownloader)
    downloader.download_article_media.return_value = [
        PIPMedia(
            original_url="https://example.com/image.jpg",
            local_path="articles/12345/images/image.jpg",
            media_type="image/jpeg",
            checksum="abc123",
        )
    ]
    return downloader


class TestPIPAggregatorInit:
    """Tests for PIPAggregator initialization."""

    def test_init_sets_output_dir(self, tmp_path, mock_ceo_client):
        """PIPAggregator stores output directory."""
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)
        assert aggregator.output_dir == tmp_path

    def test_init_sets_ceo_client(self, tmp_path, mock_ceo_client):
        """PIPAggregator stores CeoClient reference."""
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)
        assert aggregator.ceo_client is mock_ceo_client


class TestPIPAggregatorCreatePIP:
    """Tests for PIPAggregator.create_pip() method."""

    def test_create_pip_creates_directory_structure(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip() creates expected directory structure."""
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        aggregator.create_pip(
            issue_id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=sample_ceo_items,
        )

        pip_dir = tmp_path / "2026-01-15"
        assert pip_dir.exists()
        assert (pip_dir / "articles").exists()
        assert (pip_dir / "pip-manifest.json").exists()

    def test_create_pip_creates_article_directories(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip() creates directory for each article."""
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        aggregator.create_pip(
            issue_id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=sample_ceo_items,
        )

        articles_dir = tmp_path / "2026-01-15" / "articles"
        for item in sample_ceo_items:
            article_dir = articles_dir / item.ceo_id
            assert article_dir.exists()
            assert (article_dir / "ceo_record.json").exists()

    def test_create_pip_saves_ceo_records(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip() saves CEO records as JSON."""
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        aggregator.create_pip(
            issue_id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=sample_ceo_items,
        )

        record_path = (
            tmp_path
            / "2026-01-15"
            / "articles"
            / sample_ceo_items[0].ceo_id
            / "ceo_record.json"
        )
        record_data = json.loads(record_path.read_text())
        assert record_data["headline"] == sample_ceo_items[0].headline
        assert record_data["ceo_id"] == sample_ceo_items[0].ceo_id

    def test_create_pip_returns_manifest(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip() returns a PIPManifest."""
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        manifest = aggregator.create_pip(
            issue_id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=sample_ceo_items,
        )

        assert isinstance(manifest, PIPManifest)
        assert manifest.id == "2026-01-15"
        assert manifest.title == "Test Issue"
        assert manifest.date_range == ("2026-01-15", "2026-01-15")
        assert len(manifest.articles) == 3
        assert manifest.status == "sealed"

    def test_create_pip_writes_manifest_file(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip() writes manifest to pip-manifest.json."""
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        aggregator.create_pip(
            issue_id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=sample_ceo_items,
        )

        manifest_path = tmp_path / "2026-01-15" / "pip-manifest.json"
        manifest_data = json.loads(manifest_path.read_text())
        assert manifest_data["id"] == "2026-01-15"
        assert manifest_data["title"] == "Test Issue"
        assert len(manifest_data["articles"]) == 3

    def test_create_pip_sets_pdi_fields(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip() populates preservation description info."""
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        manifest = aggregator.create_pip(
            issue_id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=sample_ceo_items,
        )

        assert manifest.pdi.source_system == "CEO3"
        assert manifest.pdi.source_url == mock_ceo_client.base_url
        assert manifest.pdi.harvest_agent == "periodical-distiller"
        assert manifest.pdi.harvest_timestamp is not None

    def test_create_pip_article_paths_are_relative(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip() uses relative paths for article records."""
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        manifest = aggregator.create_pip(
            issue_id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=sample_ceo_items,
        )

        for pip_article in manifest.articles:
            assert pip_article.ceo_record_path.startswith("articles/")
            assert pip_article.ceo_record_path.endswith("/ceo_record.json")
            assert not pip_article.ceo_record_path.startswith("/")

    def test_create_pip_empty_articles(self, tmp_path, mock_ceo_client):
        """create_pip() handles empty article list."""
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        manifest = aggregator.create_pip(
            issue_id="2026-01-15",
            title="Empty Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=[],
        )

        assert manifest.id == "2026-01-15"
        assert len(manifest.articles) == 0


class TestPIPAggregatorCreatePIPForDate:
    """Tests for PIPAggregator.create_pip_for_date() method."""

    def test_create_pip_for_date_calls_client(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip_for_date() fetches articles via client."""
        mock_ceo_client.fetch_by_date = MagicMock(return_value=sample_ceo_items)
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        aggregator.create_pip_for_date(date(2026, 1, 15))

        mock_ceo_client.fetch_by_date.assert_called_once_with(date(2026, 1, 15))

    def test_create_pip_for_date_uses_date_as_issue_id(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip_for_date() uses ISO date as issue ID."""
        mock_ceo_client.fetch_by_date = MagicMock(return_value=sample_ceo_items)
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        manifest = aggregator.create_pip_for_date(date(2026, 1, 15))

        assert manifest.id == "2026-01-15"
        assert (tmp_path / "2026-01-15").exists()

    def test_create_pip_for_date_sets_title(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip_for_date() generates appropriate title."""
        mock_ceo_client.fetch_by_date = MagicMock(return_value=sample_ceo_items)
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        manifest = aggregator.create_pip_for_date(date(2026, 1, 15))

        assert "Daily Princetonian" in manifest.title
        assert "January 15, 2026" in manifest.title

    def test_create_pip_for_date_sets_date_range(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip_for_date() sets matching start and end dates."""
        mock_ceo_client.fetch_by_date = MagicMock(return_value=sample_ceo_items)
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        manifest = aggregator.create_pip_for_date(date(2026, 1, 15))

        assert manifest.date_range == ("2026-01-15", "2026-01-15")


class TestPIPAggregatorCreatePIPForDateRange:
    """Tests for PIPAggregator.create_pip_for_date_range() method."""

    def test_create_pip_for_date_range_calls_client(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip_for_date_range() fetches articles via client."""
        mock_ceo_client.fetch_by_date_range = MagicMock(return_value=sample_ceo_items)
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        aggregator.create_pip_for_date_range(date(2026, 1, 15), date(2026, 1, 17))

        mock_ceo_client.fetch_by_date_range.assert_called_once_with(
            date(2026, 1, 15), date(2026, 1, 17)
        )

    def test_create_pip_for_date_range_uses_range_as_issue_id(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip_for_date_range() uses date range as issue ID."""
        mock_ceo_client.fetch_by_date_range = MagicMock(return_value=sample_ceo_items)
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        manifest = aggregator.create_pip_for_date_range(
            date(2026, 1, 15), date(2026, 1, 17)
        )

        assert manifest.id == "2026-01-15_to_2026-01-17"
        assert (tmp_path / "2026-01-15_to_2026-01-17").exists()

    def test_create_pip_for_date_range_sets_title(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip_for_date_range() generates appropriate title."""
        mock_ceo_client.fetch_by_date_range = MagicMock(return_value=sample_ceo_items)
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        manifest = aggregator.create_pip_for_date_range(
            date(2026, 1, 15), date(2026, 1, 17)
        )

        assert "Daily Princetonian" in manifest.title
        assert "January 15, 2026" in manifest.title
        assert "January 17, 2026" in manifest.title

    def test_create_pip_for_date_range_sets_date_range(
        self, tmp_path, mock_ceo_client, sample_ceo_items
    ):
        """create_pip_for_date_range() sets correct date range."""
        mock_ceo_client.fetch_by_date_range = MagicMock(return_value=sample_ceo_items)
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)

        manifest = aggregator.create_pip_for_date_range(
            date(2026, 1, 15), date(2026, 1, 17)
        )

        assert manifest.date_range == ("2026-01-15", "2026-01-17")


class TestPIPAggregatorMediaDownload:
    """Tests for PIPAggregator media download functionality."""

    def test_init_download_media_default_true(self, tmp_path, mock_ceo_client):
        """download_media defaults to True."""
        aggregator = PIPAggregator(tmp_path, mock_ceo_client)
        assert aggregator.download_media is True

    def test_init_download_media_false(self, tmp_path, mock_ceo_client):
        """download_media can be disabled."""
        aggregator = PIPAggregator(tmp_path, mock_ceo_client, download_media=False)
        assert aggregator.download_media is False

    def test_init_accepts_media_downloader(
        self, tmp_path, mock_ceo_client, mock_media_downloader
    ):
        """PIPAggregator accepts injected MediaDownloader."""
        aggregator = PIPAggregator(
            tmp_path, mock_ceo_client, media_downloader=mock_media_downloader
        )
        assert aggregator._media_downloader is mock_media_downloader

    def test_create_pip_calls_media_downloader(
        self, tmp_path, mock_ceo_client, sample_ceo_items, mock_media_downloader
    ):
        """create_pip() calls media downloader for each article."""
        aggregator = PIPAggregator(
            tmp_path, mock_ceo_client, media_downloader=mock_media_downloader
        )

        aggregator.create_pip(
            issue_id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=sample_ceo_items,
        )

        assert mock_media_downloader.download_article_media.call_count == 3

    def test_create_pip_skips_media_download_when_disabled(
        self, tmp_path, mock_ceo_client, sample_ceo_items, mock_media_downloader
    ):
        """create_pip() skips media download when download_media is False."""
        aggregator = PIPAggregator(
            tmp_path,
            mock_ceo_client,
            download_media=False,
            media_downloader=mock_media_downloader,
        )

        manifest = aggregator.create_pip(
            issue_id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=sample_ceo_items,
        )

        mock_media_downloader.download_article_media.assert_not_called()
        for article in manifest.articles:
            assert article.media == []

    def test_create_pip_includes_media_in_manifest(
        self, tmp_path, mock_ceo_client, sample_ceo_items, mock_media_downloader
    ):
        """create_pip() includes downloaded media in manifest."""
        aggregator = PIPAggregator(
            tmp_path, mock_ceo_client, media_downloader=mock_media_downloader
        )

        manifest = aggregator.create_pip(
            issue_id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=sample_ceo_items,
        )

        for article in manifest.articles:
            assert len(article.media) == 1
            assert article.media[0].original_url == "https://example.com/image.jpg"
            assert article.media[0].checksum == "abc123"

    def test_create_pip_handles_download_failure_gracefully(
        self, tmp_path, mock_ceo_client, sample_ceo_items, mock_media_downloader
    ):
        """create_pip() handles media download failures gracefully."""
        mock_media_downloader.download_article_media.return_value = []
        aggregator = PIPAggregator(
            tmp_path, mock_ceo_client, media_downloader=mock_media_downloader
        )

        manifest = aggregator.create_pip(
            issue_id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=sample_ceo_items,
        )

        assert len(manifest.articles) == 3
        for article in manifest.articles:
            assert article.media == []

    def test_create_pip_manifest_file_includes_media(
        self, tmp_path, mock_ceo_client, sample_ceo_items, mock_media_downloader
    ):
        """create_pip() writes media to manifest file."""
        aggregator = PIPAggregator(
            tmp_path, mock_ceo_client, media_downloader=mock_media_downloader
        )

        aggregator.create_pip(
            issue_id="2026-01-15",
            title="Test Issue",
            date_range=("2026-01-15", "2026-01-15"),
            articles=sample_ceo_items,
        )

        manifest_path = tmp_path / "2026-01-15" / "pip-manifest.json"
        manifest_data = json.loads(manifest_path.read_text())

        for article in manifest_data["articles"]:
            assert len(article["media"]) == 1
            assert article["media"][0]["original_url"] == "https://example.com/image.jpg"
            assert article["media"][0]["checksum"] == "abc123"
