"""Tests for the MediaDownloader class."""

import hashlib
from unittest.mock import MagicMock

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
        with MediaDownloader(http_client=mock_http_client) as _:
            pass

        mock_http_client.close.assert_not_called()


class TestMediaDownloaderClientConfig:
    """Tests for HTTP client configuration."""

    def test_client_follows_redirects(self):
        """HTTP client is configured to follow redirects."""
        downloader = MediaDownloader()
        client = downloader._get_client()

        # httpx Client should be configured with follow_redirects=True
        assert client.follow_redirects is True

        downloader.close()


class TestBuildMediaUrls:
    """Tests for MediaDownloader._build_media_urls()."""

    def test_build_media_urls_primary(self, sample_ceo_media):
        """Primary URL is sized imgix URL."""
        downloader = MediaDownloader()

        urls = downloader._build_media_urls(sample_ceo_media)

        assert urls[0] == "https://snworksceo.imgix.net/pri/attach-uuid-456.sized-1000x1000.jpg"

    def test_build_media_urls_fallback(self, sample_ceo_media):
        """Fallback URL omits the size suffix."""
        downloader = MediaDownloader()

        urls = downloader._build_media_urls(sample_ceo_media)

        assert urls[1] == "https://snworksceo.imgix.net/pri/attach-uuid-456.jpg"

    def test_build_media_urls_png(self, sample_ceo_media):
        """URL handles different extensions."""
        sample_ceo_media.extension = "png"
        downloader = MediaDownloader()

        urls = downloader._build_media_urls(sample_ceo_media)

        assert urls[0] == "https://snworksceo.imgix.net/pri/attach-uuid-456.sized-1000x1000.png"

    def test_build_media_urls_heic_fallbacks(self, sample_ceo_media):
        """HEIC files get jpg and png fallback URLs."""
        sample_ceo_media.extension = "heic"
        downloader = MediaDownloader()

        urls = downloader._build_media_urls(sample_ceo_media)

        assert urls[0].endswith(".jpg")
        assert any("png" in u for u in urls)
        assert len(urls) == 4

    def test_build_media_urls_heic_case_insensitive(self, sample_ceo_media):
        """HEIC detection is case-insensitive."""
        sample_ceo_media.extension = "HEIC"
        downloader = MediaDownloader()

        urls = downloader._build_media_urls(sample_ceo_media)

        assert urls[0].endswith(".jpg")


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

    def test_download_article_media_heic_converted_to_jpg(
        self, tmp_path, sample_ceo_record, sample_ceo_media, mock_http_client
    ):
        """HEIC files are downloaded as JPG with correct extension and mime type."""
        sample_ceo_media.extension = "heic"
        record = sample_ceo_record.copy()
        record["dominantMedia"] = sample_ceo_media.model_dump()
        article = CeoItem.model_validate(record)

        mock_response = MagicMock()
        mock_response.content = b"fake jpg data"
        mock_http_client.get.return_value = mock_response

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader.download_article_media(article, article_dir)

        assert len(result) == 1
        # File should be saved as .jpg, not .heic
        assert result[0].local_path.endswith(".jpg")
        assert result[0].media_type == "image/jpeg"
        # URL should request .jpg extension
        assert result[0].original_url.endswith(".jpg")

        # Verify file exists with correct name
        image_path = article_dir / "images" / "test-image.jpg"
        assert image_path.exists()

    def test_download_article_media_heic_tries_fallback_urls(
        self, tmp_path, sample_ceo_record, sample_ceo_media, mock_http_client
    ):
        """HEIC files try multiple URL formats: jpg and png, sized and unsized.

        Some HEIC files uploaded to CEO3 are converted to PNG on imgix.
        The downloader should try jpg first, then png as fallbacks.

        Real-world example: article 73405 has HEIC that's stored as PNG:
        https://snworksceo.imgix.net/pri/1348d282-34ee-4cae-a78c-d4ae7c0f8e12.sized-1000x1000.png
        """
        sample_ceo_media.extension = "heic"
        sample_ceo_media.attachment_uuid = "1348d282-34ee-4cae-a78c-d4ae7c0f8e12"
        record = sample_ceo_record.copy()
        record["dominantMedia"] = sample_ceo_media.model_dump()
        article = CeoItem.model_validate(record)

        # First request (sized jpg) returns 404, second (sized png) succeeds
        mock_404_response = MagicMock()
        mock_404_response.status_code = 404
        mock_success_response = MagicMock()
        mock_success_response.content = b"fake png data"

        mock_http_client.get.side_effect = [
            httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=mock_404_response
            ),
            mock_success_response,
        ]

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader.download_article_media(article, article_dir)

        # Should succeed via fallback URL
        assert len(result) == 1
        assert result[0].local_path.endswith(".jpg")

        # Should have tried two URLs
        assert mock_http_client.get.call_count == 2

        # First call should be sized jpg
        first_call_url = mock_http_client.get.call_args_list[0][0][0]
        assert "sized-1000x1000.jpg" in first_call_url

        # Second call should be sized png
        second_call_url = mock_http_client.get.call_args_list[1][0][0]
        assert "sized-1000x1000.png" in second_call_url


class TestExtractFlourishUrls:
    """Tests for MediaDownloader._extract_flourish_urls()."""

    def test_extract_flourish_urls_with_single_chart(self):
        """Extracts a single Flourish thumbnail URL."""
        downloader = MediaDownloader()
        content = """
        <figure><div class="embed-code">
          <div class="flourish-embed flourish-chart" data-src="visualisation/25705049">
            <script src="https://public.flourish.studio/resources/embed.js"></script>
            <noscript>
              <img src="https://public.flourish.studio/visualisation/25705049/thumbnail"
                   width="100%" alt="chart visualization"/>
            </noscript>
          </div>
        </div></figure>
        """

        result = downloader._extract_flourish_urls(content)

        assert len(result) == 1
        assert result[0] == (
            "25705049",
            "https://public.flourish.studio/visualisation/25705049/thumbnail",
        )

    def test_extract_flourish_urls_with_multiple_charts(self):
        """Extracts multiple Flourish thumbnail URLs."""
        downloader = MediaDownloader()
        content = """
        <figure>
          <noscript>
            <img src="https://public.flourish.studio/visualisation/11111111/thumbnail"/>
          </noscript>
        </figure>
        <figure>
          <noscript>
            <img src="https://public.flourish.studio/visualisation/22222222/thumbnail"/>
          </noscript>
        </figure>
        """

        result = downloader._extract_flourish_urls(content)

        assert len(result) == 2
        assert result[0][0] == "11111111"
        assert result[1][0] == "22222222"

    def test_extract_flourish_urls_with_no_charts(self):
        """Returns empty list when no Flourish charts are present."""
        downloader = MediaDownloader()
        content = "<p>This is just regular HTML content with no charts.</p>"

        result = downloader._extract_flourish_urls(content)

        assert result == []

    def test_extract_flourish_urls_with_none_content(self):
        """Returns empty list when content is None."""
        downloader = MediaDownloader()

        result = downloader._extract_flourish_urls(None)

        assert result == []

    def test_extract_flourish_urls_with_empty_content(self):
        """Returns empty list when content is empty string."""
        downloader = MediaDownloader()

        result = downloader._extract_flourish_urls("")

        assert result == []

    def test_extract_flourish_urls_deduplicates(self):
        """Removes duplicate visualization IDs."""
        downloader = MediaDownloader()
        content = """
        <img src="https://public.flourish.studio/visualisation/12345/thumbnail"/>
        <img src="https://public.flourish.studio/visualisation/12345/thumbnail"/>
        """

        result = downloader._extract_flourish_urls(content)

        assert len(result) == 1
        assert result[0][0] == "12345"


class TestDownloadFlourishCharts:
    """Tests for MediaDownloader._download_flourish_charts()."""

    @pytest.fixture
    def sample_article_with_flourish(self, sample_ceo_record):
        """Create a sample CeoItem with Flourish chart in content."""
        record = sample_ceo_record.copy()
        record["content"] = """
        <p>Here is some analysis.</p>
        <figure><div class="embed-code">
          <div class="flourish-embed flourish-chart" data-src="visualisation/25705049">
            <noscript>
              <img src="https://public.flourish.studio/visualisation/25705049/thumbnail"/>
            </noscript>
          </div>
        </div></figure>
        <p>More text after chart.</p>
        """
        return CeoItem.model_validate(record)

    @pytest.fixture
    def sample_article_with_multiple_flourish(self, sample_ceo_record):
        """Create a sample CeoItem with multiple Flourish charts."""
        record = sample_ceo_record.copy()
        record["content"] = """
        <img src="https://public.flourish.studio/visualisation/11111111/thumbnail"/>
        <img src="https://public.flourish.studio/visualisation/22222222/thumbnail"/>
        """
        return CeoItem.model_validate(record)

    def test_download_flourish_charts_success(
        self, tmp_path, sample_article_with_flourish, mock_http_client
    ):
        """Downloads Flourish chart and returns PIPMedia."""
        mock_response = MagicMock()
        mock_response.content = b"fake png data"
        mock_http_client.get.return_value = mock_response

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader._download_flourish_charts(
            sample_article_with_flourish, article_dir
        )

        assert len(result) == 1
        assert result[0].original_url == (
            "https://public.flourish.studio/visualisation/25705049/thumbnail"
        )
        assert result[0].local_path == "articles/12345/charts/flourish-25705049.png"
        assert result[0].media_type == "image/png"
        assert result[0].checksum is not None

        chart_path = article_dir / "charts" / "flourish-25705049.png"
        assert chart_path.exists()
        assert chart_path.read_bytes() == b"fake png data"

    def test_download_flourish_charts_creates_charts_dir(
        self, tmp_path, sample_article_with_flourish, mock_http_client
    ):
        """Creates charts directory if it doesn't exist."""
        mock_response = MagicMock()
        mock_response.content = b"fake png data"
        mock_http_client.get.return_value = mock_response

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        downloader._download_flourish_charts(sample_article_with_flourish, article_dir)

        charts_dir = article_dir / "charts"
        assert charts_dir.exists()
        assert charts_dir.is_dir()

    def test_download_flourish_charts_multiple(
        self, tmp_path, sample_article_with_multiple_flourish, mock_http_client
    ):
        """Downloads multiple Flourish charts."""
        mock_response = MagicMock()
        mock_response.content = b"fake png data"
        mock_http_client.get.return_value = mock_response

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader._download_flourish_charts(
            sample_article_with_multiple_flourish, article_dir
        )

        assert len(result) == 2
        assert result[0].local_path == "articles/12345/charts/flourish-11111111.png"
        assert result[1].local_path == "articles/12345/charts/flourish-22222222.png"

    def test_download_flourish_charts_no_charts(
        self, tmp_path, sample_ceo_item_no_media
    ):
        """Returns empty list when article has no Flourish charts."""
        downloader = MediaDownloader()
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader._download_flourish_charts(
            sample_ceo_item_no_media, article_dir
        )

        assert result == []

    def test_download_flourish_charts_http_error(
        self, tmp_path, sample_article_with_flourish, mock_http_client
    ):
        """Returns empty list on HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        error = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_http_client.get.side_effect = error

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader._download_flourish_charts(
            sample_article_with_flourish, article_dir
        )

        assert result == []

    def test_download_flourish_charts_partial_failure(
        self, tmp_path, sample_article_with_multiple_flourish, mock_http_client
    ):
        """Downloads successful charts even when some fail."""
        mock_response = MagicMock()
        mock_response.content = b"fake png data"

        mock_error_response = MagicMock()
        mock_error_response.status_code = 500

        # First call succeeds, second fails
        mock_http_client.get.side_effect = [
            mock_response,
            httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=mock_error_response
            ),
        ]

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader._download_flourish_charts(
            sample_article_with_multiple_flourish, article_dir
        )

        # Only the first chart should be returned
        assert len(result) == 1
        assert result[0].local_path == "articles/12345/charts/flourish-11111111.png"


class TestDownloadArticleMediaWithFlourish:
    """Tests for download_article_media including Flourish charts."""

    @pytest.fixture
    def sample_article_with_media_and_flourish(self, sample_ceo_record, sample_ceo_media):
        """Create a sample CeoItem with both dominant media and Flourish chart."""
        record = sample_ceo_record.copy()
        record["dominantMedia"] = sample_ceo_media.model_dump()
        record["content"] = """
        <p>Article text.</p>
        <img src="https://public.flourish.studio/visualisation/99999999/thumbnail"/>
        """
        return CeoItem.model_validate(record)

    def test_download_article_media_includes_flourish(
        self, tmp_path, sample_article_with_media_and_flourish, mock_http_client
    ):
        """Downloads both dominant media and Flourish charts."""
        mock_response = MagicMock()
        mock_response.content = b"fake image data"
        mock_http_client.get.return_value = mock_response

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader.download_article_media(
            sample_article_with_media_and_flourish, article_dir
        )

        assert len(result) == 2
        # First should be dominant media
        assert "images/test-image.jpg" in result[0].local_path
        # Second should be Flourish chart
        assert "charts/flourish-99999999.png" in result[1].local_path

    def test_download_article_media_flourish_only(
        self, tmp_path, sample_ceo_record, mock_http_client
    ):
        """Downloads Flourish charts when no dominant media."""
        record = sample_ceo_record.copy()
        record["content"] = """
        <img src="https://public.flourish.studio/visualisation/12345678/thumbnail"/>
        """
        article = CeoItem.model_validate(record)

        mock_response = MagicMock()
        mock_response.content = b"fake png data"
        mock_http_client.get.return_value = mock_response

        downloader = MediaDownloader(http_client=mock_http_client)
        article_dir = tmp_path / "articles" / "12345"
        article_dir.mkdir(parents=True)

        result = downloader.download_article_media(article, article_dir)

        assert len(result) == 1
        assert "charts/flourish-12345678.png" in result[0].local_path
