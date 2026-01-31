"""Tests for the MediaDownloader class."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from periodical_distiller.aggregators import MediaDownloader
from schemas.ceo_item import CeoItem, CeoMedia


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
def sample_ceo_item_with_media(sample_ceo_record, sample_ceo_media):
    """Create a sample CeoItem with dominant media."""
    record = sample_ceo_record.copy()
    record["dominantMedia"] = sample_ceo_media.model_dump()
    return CeoItem.model_validate(record)


@pytest.fixture
def sample_ceo_item_no_media(sample_ceo_record):
    """Create a sample CeoItem without dominant media."""
    return CeoItem.model_validate(sample_ceo_record)


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    return MagicMock(spec=httpx.Client)


class TestMediaDownloaderInit:
    """Tests for MediaDownloader initialization."""

    def test_init_without_client(self):
        """MediaDownloader can be created without an HTTP client."""
        downloader = MediaDownloader()
        assert downloader._client is None
        assert downloader._owns_client is True

    def test_init_with_client(self, mock_http_client):
        """MediaDownloader accepts an injected HTTP client."""
        downloader = MediaDownloader(http_client=mock_http_client)
        assert downloader._client is mock_http_client
        assert downloader._owns_client is False


class TestMediaDownloaderContextManager:
    """Tests for MediaDownloader context manager."""

    def test_context_manager_closes_owned_client(self):
        """Context manager closes client when we own it."""
        with MediaDownloader() as downloader:
            client = downloader._get_client()
            assert client is not None

        assert downloader._client is None

    def test_context_manager_does_not_close_injected_client(self, mock_http_client):
        """Context manager does not close injected client."""
        with MediaDownloader(http_client=mock_http_client) as downloader:
            pass

        mock_http_client.close.assert_not_called()


class TestBuildMediaUrl:
    """Tests for MediaDownloader._build_media_url()."""

    def test_build_media_url(self, sample_ceo_media):
        """URL is constructed correctly from CeoMedia fields."""
        downloader = MediaDownloader()

        url = downloader._build_media_url(sample_ceo_media)

        expected = "https://snworksceo.imgix.net/pri/attach-uuid-456.sized-1000x1000.jpg"
        assert url == expected

    def test_build_media_url_with_png(self, sample_ceo_media):
        """URL handles different extensions."""
        sample_ceo_media.extension = "png"
        downloader = MediaDownloader()

        url = downloader._build_media_url(sample_ceo_media)

        expected = "https://snworksceo.imgix.net/pri/attach-uuid-456.sized-1000x1000.png"
        assert url == expected


class TestComputeChecksum:
    """Tests for MediaDownloader._compute_checksum()."""

    def test_compute_checksum(self, tmp_path):
        """Checksum is computed correctly."""
        test_file = tmp_path / "test.txt"
        test_content = b"Hello, World!"
        test_file.write_bytes(test_content)

        downloader = MediaDownloader()
        checksum = downloader._compute_checksum(test_file)

        expected = hashlib.sha256(test_content).hexdigest()
        assert checksum == expected

    def test_compute_checksum_binary_file(self, tmp_path):
        """Checksum works on binary files."""
        test_file = tmp_path / "test.bin"
        test_content = bytes(range(256))
        test_file.write_bytes(test_content)

        downloader = MediaDownloader()
        checksum = downloader._compute_checksum(test_file)

        expected = hashlib.sha256(test_content).hexdigest()
        assert checksum == expected


class TestGetMediaType:
    """Tests for MediaDownloader._get_media_type()."""

    def test_get_media_type_jpg(self):
        """Returns correct MIME type for jpg."""
        downloader = MediaDownloader()
        assert downloader._get_media_type("jpg") == "image/jpeg"

    def test_get_media_type_jpeg(self):
        """Returns correct MIME type for jpeg."""
        downloader = MediaDownloader()
        assert downloader._get_media_type("jpeg") == "image/jpeg"

    def test_get_media_type_png(self):
        """Returns correct MIME type for png."""
        downloader = MediaDownloader()
        assert downloader._get_media_type("png") == "image/png"

    def test_get_media_type_gif(self):
        """Returns correct MIME type for gif."""
        downloader = MediaDownloader()
        assert downloader._get_media_type("gif") == "image/gif"

    def test_get_media_type_webp(self):
        """Returns correct MIME type for webp."""
        downloader = MediaDownloader()
        assert downloader._get_media_type("webp") == "image/webp"

    def test_get_media_type_unknown(self):
        """Returns application/octet-stream for unknown extensions."""
        downloader = MediaDownloader()
        assert downloader._get_media_type("xyz") == "application/octet-stream"

    def test_get_media_type_case_insensitive(self):
        """Extension matching is case-insensitive."""
        downloader = MediaDownloader()
        assert downloader._get_media_type("JPG") == "image/jpeg"
        assert downloader._get_media_type("PNG") == "image/png"


class TestDownloadArticleMedia:
    """Tests for MediaDownloader.download_article_media()."""

    def test_download_article_media_no_dominant_media(
        self, tmp_path, sample_ceo_item_no_media
    ):
        """Returns empty list when article has no dominant media."""
        downloader = MediaDownloader()
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader.download_article_media(sample_ceo_item_no_media, article_dir)

        assert result == []

    def test_download_article_media_success(
        self, tmp_path, sample_ceo_item_with_media, mock_http_client
    ):
        """Downloads media and returns PIPMedia on success."""
        mock_response = MagicMock()
        mock_response.content = b"fake image data"
        mock_http_client.get.return_value = mock_response

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader.download_article_media(
            sample_ceo_item_with_media, article_dir
        )

        assert len(result) == 1
        assert result[0].original_url == (
            "https://snworksceo.imgix.net/pri/attach-uuid-456.sized-1000x1000.jpg"
        )
        assert result[0].local_path == "articles/12345/images/test-image.jpg"
        assert result[0].media_type == "image/jpeg"
        assert result[0].checksum is not None

        image_path = article_dir / "images" / "test-image.jpg"
        assert image_path.exists()
        assert image_path.read_bytes() == b"fake image data"

    def test_download_article_media_creates_images_dir(
        self, tmp_path, sample_ceo_item_with_media, mock_http_client
    ):
        """Creates images directory if it doesn't exist."""
        mock_response = MagicMock()
        mock_response.content = b"fake image data"
        mock_http_client.get.return_value = mock_response

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        downloader.download_article_media(sample_ceo_item_with_media, article_dir)

        images_dir = article_dir / "images"
        assert images_dir.exists()
        assert images_dir.is_dir()

    def test_download_article_media_http_error(
        self, tmp_path, sample_ceo_item_with_media, mock_http_client
    ):
        """Returns empty list on HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError("Not Found", request=MagicMock(), response=mock_response)
        mock_http_client.get.side_effect = error

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader.download_article_media(
            sample_ceo_item_with_media, article_dir
        )

        assert result == []

    def test_download_article_media_request_error(
        self, tmp_path, sample_ceo_item_with_media, mock_http_client
    ):
        """Returns empty list on network error."""
        error = httpx.RequestError("Connection failed")
        mock_http_client.get.side_effect = error

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader.download_article_media(
            sample_ceo_item_with_media, article_dir
        )

        assert result == []

    def test_download_article_media_checksum_matches_content(
        self, tmp_path, sample_ceo_item_with_media, mock_http_client
    ):
        """Checksum matches downloaded content."""
        test_content = b"specific test content for checksum"
        mock_response = MagicMock()
        mock_response.content = test_content
        mock_http_client.get.return_value = mock_response

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader.download_article_media(
            sample_ceo_item_with_media, article_dir
        )

        expected_checksum = hashlib.sha256(test_content).hexdigest()
        assert result[0].checksum == expected_checksum
