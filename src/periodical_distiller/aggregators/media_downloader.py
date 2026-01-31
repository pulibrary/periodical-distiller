"""Media downloader for fetching article images from CEO3."""

import hashlib
import logging
from pathlib import Path

import httpx

from schemas.ceo_item import CeoItem, CeoMedia
from schemas.pip import PIPMedia

logger = logging.getLogger(__name__)

IMGIX_BASE_URL = "https://snworksceo.imgix.net"


class MediaDownloader:
    """Downloads and stores media files from CEO3 articles.

    CEO3 uses imgix CDN for media delivery. This class downloads article
    images and computes checksums for integrity verification.

    Example:
        downloader = MediaDownloader()
        article_dir = Path("./pips/2026-01-15/articles/12345")
        media_list = downloader.download_article_media(article, article_dir)
    """

    def __init__(self, http_client: httpx.Client | None = None):
        """Initialize the media downloader.

        Args:
            http_client: Optional HTTP client for downloading media.
                         If not provided, one will be created internally.
        """
        self._client = http_client
        self._owns_client = http_client is None

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client

    def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "MediaDownloader":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.close()

    def download_article_media(
        self,
        article: CeoItem,
        article_dir: Path,
    ) -> list[PIPMedia]:
        """Download media files for an article.

        Downloads the dominant media image from the article and stores it
        in the article's images directory.

        Args:
            article: The CEO article containing media references
            article_dir: Base directory for the article (e.g., articles/{ceo_id})

        Returns:
            List of PIPMedia objects describing downloaded files
        """
        if article.dominant_media is None:
            logger.debug(f"Article {article.ceo_id} has no dominant media")
            return []

        media = article.dominant_media
        media_url = self._build_media_url(media)

        images_dir = article_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{media.base_name}.{media.extension}"
        local_path = images_dir / filename

        try:
            self._download_file(media_url, local_path)
            checksum = self._compute_checksum(local_path)

            relative_path = f"articles/{article.ceo_id}/images/{filename}"
            media_type = self._get_media_type(media.extension)

            pip_media = PIPMedia(
                original_url=media_url,
                local_path=relative_path,
                media_type=media_type,
                checksum=checksum,
            )

            logger.debug(
                f"Downloaded media for article {article.ceo_id}: {filename}"
            )
            return [pip_media]

        except httpx.HTTPStatusError as e:
            logger.warning(
                f"Failed to download media for article {article.ceo_id}: "
                f"HTTP {e.response.status_code}"
            )
            return []
        except httpx.RequestError as e:
            logger.warning(
                f"Failed to download media for article {article.ceo_id}: {e}"
            )
            return []

    def _build_media_url(self, media: CeoMedia) -> str:
        """Build the CDN URL for a media item.

        CEO3 uses imgix CDN with URLs in the format:
        https://snworksceo.imgix.net/pri/{attachment_uuid}.sized-1000x1000.{extension}

        The 'pri' prefix is the publication identifier for Daily Princetonian.
        The 'sized-1000x1000' suffix requests a standardized image size.

        Args:
            media: The CeoMedia object

        Returns:
            The full URL for downloading the media
        """
        return f"{IMGIX_BASE_URL}/pri/{media.attachment_uuid}.sized-1000x1000.{media.extension}"

    def _download_file(self, url: str, destination: Path) -> None:
        """Download a file from URL to local path.

        Args:
            url: URL to download from
            destination: Local file path to save to

        Raises:
            httpx.HTTPStatusError: If the request returns an error status
            httpx.RequestError: If there's a network error
        """
        client = self._get_client()
        response = client.get(url)
        response.raise_for_status()

        destination.write_bytes(response.content)

    def _compute_checksum(self, file_path: Path) -> str:
        """Compute SHA-256 checksum of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hex-encoded SHA-256 hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _get_media_type(self, extension: str) -> str:
        """Get MIME type for a file extension.

        Args:
            extension: File extension (without dot)

        Returns:
            MIME type string
        """
        mime_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        return mime_types.get(extension.lower(), "application/octet-stream")
