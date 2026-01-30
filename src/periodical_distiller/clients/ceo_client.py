"""CEO API client for fetching Daily Princetonian content."""

from datetime import date, datetime
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from schemas.ceo_item import CeoItem

from .client import Client
from .exceptions import ValidationError


class CeoClient(Client):
    """Client for the CEO headless CMS API.

    Fetches article content from the Daily Princetonian's CEO API,
    validating responses against the CeoItem schema. Uses the section
    endpoint with client-side date filtering.

    Example:
        config = {"base_url": "https://www.dailyprincetonian.com"}
        with CeoClient(config) as client:
            items = client.fetch_by_date(date(2026, 1, 15))
    """

    API_PATH = "/section/news.json"
    DEFAULT_PER_PAGE = 100

    def fetch(
        self,
        date_start: date | None = None,
        date_end: date | None = None,
        limit: int | None = None,
        offset: int = 0,
        validate: bool = True,
    ) -> list[CeoItem] | list[dict[str, Any]]:
        """Fetch articles from the CEO API.

        Args:
            date_start: Filter articles published on or after this date
            date_end: Filter articles published on or before this date
            limit: Maximum number of articles to return. If None, fetches all.
            offset: Number of articles to skip (for manual pagination)
            validate: If True, validate responses against CeoItem schema

        Returns:
            List of CeoItem objects if validate=True, otherwise list of dicts

        Raises:
            ValidationError: If validate=True and response fails schema validation
            APIError: If the API returns a non-2xx response
            ConnectionError: If the network connection fails
        """
        all_items: list[dict[str, Any]] = []
        start_page = (offset // self.DEFAULT_PER_PAGE) + 1
        current_page = start_page
        items_remaining = limit
        reached_older_articles = False

        while not reached_older_articles:
            per_page = self.DEFAULT_PER_PAGE
            if limit is not None and items_remaining is not None:
                per_page = min(items_remaining, self.DEFAULT_PER_PAGE)

            params = self._build_params(per_page, current_page)
            response = self.get(self.API_PATH, params=params)
            data = response.json()

            articles = data.get("articles", [])
            if not articles:
                break

            for article in articles:
                pub_date = self._parse_published_date(article.get("published_at"))

                if date_end is not None and pub_date > date_end:
                    continue

                if date_start is not None and pub_date < date_start:
                    reached_older_articles = True
                    break

                all_items.append(article)

                if limit is not None:
                    items_remaining = limit - len(all_items)
                    if items_remaining <= 0:
                        all_items = all_items[:limit]
                        reached_older_articles = True
                        break

            current_page += 1
            pagination = data.get("pagination", {})
            if current_page > pagination.get("last", current_page):
                break

        if validate:
            return self._validate_items(all_items)

        return all_items

    def _parse_published_date(self, published_at: str | None) -> date:
        """Parse the published_at timestamp to a date."""
        if not published_at:
            return date.min
        try:
            dt = datetime.strptime(published_at, "%Y-%m-%d %H:%M:%S")
            return dt.date()
        except ValueError:
            return date.min

    def fetch_by_date(
        self, target_date: date, validate: bool = True
    ) -> list[CeoItem] | list[dict[str, Any]]:
        """Fetch articles published on a specific date.

        Args:
            target_date: The date to fetch articles for
            validate: If True, validate responses against CeoItem schema

        Returns:
            List of CeoItem objects if validate=True, otherwise list of dicts
        """
        return self.fetch(
            date_start=target_date,
            date_end=target_date,
            validate=validate,
        )

    def fetch_by_date_range(
        self,
        start: date,
        end: date,
        validate: bool = True,
    ) -> list[CeoItem] | list[dict[str, Any]]:
        """Fetch articles published within a date range.

        Args:
            start: Start date (inclusive)
            end: End date (inclusive)
            validate: If True, validate responses against CeoItem schema

        Returns:
            List of CeoItem objects if validate=True, otherwise list of dicts
        """
        return self.fetch(
            date_start=start,
            date_end=end,
            validate=validate,
        )

    def _build_params(
        self,
        per_page: int,
        page: int,
    ) -> dict[str, Any]:
        """Build query parameters for the CEO API section request.

        The section API uses:
        - page: Page number (1-indexed)
        - perPage: Items per page
        """
        return {
            "page": page,
            "perPage": per_page,
        }

    def _validate_items(self, items: list[dict[str, Any]]) -> list[CeoItem]:
        """Validate a list of items against the CeoItem schema.

        Args:
            items: List of raw item dictionaries

        Returns:
            List of validated CeoItem objects

        Raises:
            ValidationError: If any item fails validation
        """
        validated: list[CeoItem] = []

        for i, item in enumerate(items):
            try:
                validated.append(CeoItem.model_validate(item))
            except PydanticValidationError as e:
                item_id = item.get("id", f"index {i}")
                raise ValidationError(
                    f"Item {item_id} failed validation",
                    errors=[str(err) for err in e.errors()],
                ) from e

        return validated
