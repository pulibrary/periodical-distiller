"""PIP Aggregator for assembling Primary Information Packages."""

import json
import logging
from datetime import date, datetime
from pathlib import Path

from periodical_distiller.aggregators.media_downloader import MediaDownloader
from periodical_distiller.clients import CeoClient
from schemas.ceo_item import CeoItem
from schemas.pip import PIPArticle, PIPManifest, PreservationDescriptionInfo

logger = logging.getLogger(__name__)


class PIPAggregator:
    """Aggregates CEO3 content into Primary Information Packages.

    The aggregator fetches articles from CEO3 and assembles them into
    a directory structure with a manifest file for downstream processing.

    Example:
        config = {"base_url": "https://www.dailyprincetonian.com"}
        with CeoClient(config) as client:
            aggregator = PIPAggregator(Path("./workspace/pips"), client)
            manifest = aggregator.create_pip_for_date(date(2026, 1, 15))
    """

    def __init__(
        self,
        output_dir: Path,
        ceo_client: CeoClient,
        download_media: bool = True,
        media_downloader: MediaDownloader | None = None,
    ):
        """Initialize the PIP aggregator.

        Args:
            output_dir: Base directory for PIP output
            ceo_client: Client for fetching CEO3 content
            download_media: Whether to download article media (default: True)
            media_downloader: Optional MediaDownloader instance for dependency injection
        """
        self.output_dir = output_dir
        self.ceo_client = ceo_client
        self.download_media = download_media
        self._media_downloader = media_downloader
        self._owns_downloader = media_downloader is None and download_media

    def create_pip(
        self,
        issue_id: str,
        title: str,
        date_range: tuple[str, str],
        articles: list[CeoItem],
    ) -> PIPManifest:
        """Create a PIP from a list of CEO articles.

        Args:
            issue_id: Identifier for the issue (e.g., "2026-01-15")
            title: Display title for the issue
            date_range: Tuple of (start_date, end_date) as ISO strings
            articles: List of CeoItem objects to include

        Returns:
            The completed PIPManifest
        """
        pip_dir = self.output_dir / issue_id
        articles_dir = pip_dir / "articles"
        articles_dir.mkdir(parents=True, exist_ok=True)

        pip_articles: list[PIPArticle] = []

        downloader = self._get_media_downloader() if self.download_media else None

        for article in articles:
            article_dir = articles_dir / article.ceo_id
            article_dir.mkdir(exist_ok=True)

            ceo_record_path = article_dir / "ceo_record.json"
            ceo_record_path.write_text(
                article.model_dump_json(indent=2, by_alias=True)
            )

            media_list = []
            if downloader is not None:
                media_list = downloader.download_article_media(article, article_dir)

            relative_path = f"articles/{article.ceo_id}/ceo_record.json"
            pip_articles.append(
                PIPArticle(
                    ceo_id=article.ceo_id,
                    ceo_record_path=relative_path,
                    media=media_list,
                )
            )
            logger.debug(f"Saved article {article.ceo_id}: {article.headline}")

        pdi = PreservationDescriptionInfo(
            source_system="CEO3",
            source_url=self.ceo_client.base_url,
            harvest_timestamp=datetime.now(),
            harvest_agent="periodical-distiller",
        )

        manifest = PIPManifest(
            id=issue_id,
            title=title,
            date_range=date_range,
            articles=pip_articles,
            pdi=pdi,
            status="sealed",
        )

        manifest_path = pip_dir / "pip-manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2))

        logger.info(
            f"Created PIP {issue_id} with {len(pip_articles)} articles at {pip_dir}"
        )

        return manifest

    def create_pip_for_date(self, target_date: date) -> PIPManifest:
        """Fetch articles for a date and create PIP.

        Args:
            target_date: The publication date to fetch

        Returns:
            The completed PIPManifest
        """
        articles = self.ceo_client.fetch_by_date(target_date)
        issue_id = target_date.isoformat()
        date_str = target_date.isoformat()

        title = f"The Daily Princetonian - {target_date.strftime('%B %d, %Y')}"

        return self.create_pip(
            issue_id=issue_id,
            title=title,
            date_range=(date_str, date_str),
            articles=articles,
        )

    def create_pip_for_date_range(
        self, start: date, end: date
    ) -> PIPManifest:
        """Fetch articles for date range and create PIP.

        Args:
            start: Start date (inclusive)
            end: End date (inclusive)

        Returns:
            The completed PIPManifest
        """
        articles = self.ceo_client.fetch_by_date_range(start, end)
        issue_id = f"{start.isoformat()}_to_{end.isoformat()}"

        title = (
            f"The Daily Princetonian - "
            f"{start.strftime('%B %d, %Y')} to {end.strftime('%B %d, %Y')}"
        )

        return self.create_pip(
            issue_id=issue_id,
            title=title,
            date_range=(start.isoformat(), end.isoformat()),
            articles=articles,
        )

    def _get_media_downloader(self) -> MediaDownloader:
        """Get or create the media downloader instance."""
        if self._media_downloader is None:
            self._media_downloader = MediaDownloader()
        return self._media_downloader
