"""Media downloader for fetching article images from CEO3."""

import hashlib
import logging
import re
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
            self._client = httpx.Client(timeout=30.0, follow_redirects=True)
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
        in the article's images directory. Also downloads Flourish chart
        thumbnails from embedded visualizations.

        Args:
            article: The CEO article containing media references
            article_dir: Base directory for the article (e.g., articles/{ceo_id})

        Returns:
            List of PIPMedia objects describing downloaded files
        """
        media_list: list[PIPMedia] = []

        # Download dominant media if present
        if article.dominant_media is not None:
            dominant_media = self._download_dominant_media(
                article, article_dir
            )
            if dominant_media:
                media_list.append(dominant_media)
        else:
            logger.debug(f"Article {article.ceo_id} has no dominant media")

        # Download Flourish chart thumbnails
        flourish_media = self._download_flourish_charts(article, article_dir)
        media_list.extend(flourish_media)

        return media_list

    def _download_dominant_media(
        self,
        article: CeoItem,
        article_dir: Path,
    ) -> PIPMedia | None:
        """Download the dominant media image for an article.

        Tries multiple URL formats if the primary URL fails with 404.

        Args:
            article: The CEO article with dominant media
            article_dir: Base directory for the article

        Returns:
            PIPMedia object if successful, None otherwise
        """
        media = article.dominant_media
        if media is None:
            return None

        media_urls = self._build_media_urls(media)

        images_dir = article_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # HEIC files are converted to JPG by imgix
        output_extension = "jpg" if media.extension.lower() == "heic" else media.extension
        filename = f"{media.base_name}.{output_extension}"
        local_path = images_dir / filename

        last_error: Exception | None = None

        for media_url in media_urls:
            try:
                self._download_file(media_url, local_path)
                checksum = self._compute_checksum(local_path)

                relative_path = f"articles/{article.ceo_id}/images/{filename}"
                media_type = self._get_media_type(output_extension)

                pip_media = PIPMedia(
                    original_url=media_url,
                    local_path=relative_path,
                    media_type=media_type,
                    checksum=checksum,
                )

                logger.debug(
                    f"Downloaded media for article {article.ceo_id}: {filename}"
                )
                return pip_media

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 404:
                    # Try next URL
                    continue
                # For other HTTP errors, don't try fallbacks
                break
            except httpx.RequestError as e:
                last_error = e
                break

        # All URLs failed
        if isinstance(last_error, httpx.HTTPStatusError):
            logger.warning(
                f"Failed to download media for article {article.ceo_id}: "
                f"HTTP {last_error.response.status_code}"
            )
        elif last_error is not None:
            logger.warning(
                f"Failed to download media for article {article.ceo_id}: {last_error}"
            )

        return None

    def _extract_flourish_urls(self, content: str | None) -> list[tuple[str, str]]:
        """Extract Flourish visualization IDs and thumbnail URLs from content.

        Searches for Flourish embed patterns in the HTML content and extracts
        the visualization IDs to construct thumbnail URLs.

        Args:
            content: HTML content from a CEO article

        Returns:
            List of (visualization_id, thumbnail_url) tuples
        """
        if not content:
            return []

        # Match Flourish thumbnail URLs in noscript tags
        pattern = r'https://public\.flourish\.studio/visualisation/(\d+)/thumbnail'
        matches = re.findall(pattern, content)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_matches: list[str] = []
        for vid in matches:
            if vid not in seen:
                seen.add(vid)
                unique_matches.append(vid)

        return [
            (vid, f"https://public.flourish.studio/visualisation/{vid}/thumbnail")
            for vid in unique_matches
        ]

    def _download_flourish_charts(
        self,
        article: CeoItem,
        article_dir: Path,
    ) -> list[PIPMedia]:
        """Download Flourish chart thumbnails from article content.

        Args:
            article: The CEO article containing embedded Flourish charts
            article_dir: Base directory for the article

        Returns:
            List of PIPMedia objects for downloaded charts
        """
        flourish_urls = self._extract_flourish_urls(article.content)

        if not flourish_urls:
            return []

        charts_dir = article_dir / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)

        media_list: list[PIPMedia] = []

        for viz_id, url in flourish_urls:
            filename = f"flourish-{viz_id}.png"
            local_path = charts_dir / filename

            try:
                self._download_file(url, local_path)
                checksum = self._compute_checksum(local_path)

                relative_path = f"articles/{article.ceo_id}/charts/{filename}"

                pip_media = PIPMedia(
                    original_url=url,
                    local_path=relative_path,
                    media_type="image/png",
                    checksum=checksum,
                )

                media_list.append(pip_media)
                logger.debug(
                    f"Downloaded Flourish chart for article {article.ceo_id}: {filename}"
                )

            except httpx.HTTPStatusError as e:
                logger.warning(
                    f"Failed to download Flourish chart {viz_id} for article "
                    f"{article.ceo_id}: HTTP {e.response.status_code}"
                )
            except httpx.RequestError as e:
                logger.warning(
                    f"Failed to download Flourish chart {viz_id} for article "
                    f"{article.ceo_id}: {e}"
                )

        return media_list

    def _build_media_urls(self, media: CeoMedia) -> list[str]:
        """Build CDN URLs for a media item, including fallbacks.

        CEO3 uses imgix CDN with URLs in the format:
        https://snworksceo.imgix.net/pri/{attachment_uuid}.sized-1000x1000.{extension}

        The 'pri' prefix is the publication identifier for Daily Princetonian.
        The 'sized-1000x1000' suffix requests a standardized image size.

        For HEIC files (Apple's image format), imgix converts them to other
        formats. We try jpg first, then png as fallbacks.

        Args:
            media: The CeoMedia object

        Returns:
            List of URLs to try in order (primary first, then fallbacks)
        """
        uuid = media.attachment_uuid

        if media.extension.lower() == "heic":
            # HEIC files may be stored as jpg or png on imgix
            return [
                f"{IMGIX_BASE_URL}/pri/{uuid}.sized-1000x1000.jpg",
                f"{IMGIX_BASE_URL}/pri/{uuid}.sized-1000x1000.png",
                f"{IMGIX_BASE_URL}/pri/{uuid}.jpg",
                f"{IMGIX_BASE_URL}/pri/{uuid}.png",
            ]

        extension = media.extension

        # Primary URL with size suffix, fallback without
        return [
            f"{IMGIX_BASE_URL}/pri/{uuid}.sized-1000x1000.{extension}",
            f"{IMGIX_BASE_URL}/pri/{uuid}.{extension}",
        ]

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
