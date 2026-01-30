"""CEO3 API client for fetching Daily Princetonian content."""

from datetime import date
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from schemas.ceo_item import CeoItem

from .client import Client
from .exceptions import ValidationError


class CeoClient(Client):
    """Client for the CEO3 headless CMS API.

    Fetches article content from the Daily Princetonian's CEO3 API,
    validating responses against the CeoItem schema.

    Example:
        config = {"base_url": "https://www.dailyprincetonian.com"}
        with CeoClient(config) as client:
            items = client.fetch_by_date(date(2026, 1, 15))
    """

    API_PATH = "/api/content/v1/content"
    DEFAULT_LIMIT = 100

    def fetch(
        self,
        date_start: date | None = None,
        date_end: date | None = None,
        limit: int | None = None,
        offset: int = 0,
        validate: bool = True,
    ) -> list[CeoItem] | list[dict[str, Any]]:
        """Fetch articles from the CEO3 API.

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
        current_offset = offset
        page_size = min(limit or self.DEFAULT_LIMIT, self.DEFAULT_LIMIT)
        items_remaining = limit

        while True:
            params = self._build_params(date_start, date_end, page_size, current_offset)
            response = self.get(self.API_PATH, params=params)
            data = response.json()

            items = data if isinstance(data, list) else data.get("items", [])

            if not items:
                break

            all_items.extend(items)
            current_offset += len(items)

            if limit is not None:
                items_remaining = limit - len(all_items)
                if items_remaining <= 0:
                    all_items = all_items[:limit]
                    break
                page_size = min(items_remaining, self.DEFAULT_LIMIT)

            if len(items) < self.DEFAULT_LIMIT:
                break

        if validate:
            return self._validate_items(all_items)

        return all_items

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
        date_start: date | None,
        date_end: date | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        """Build query parameters for the API request."""
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        if date_start is not None:
            params["start_date"] = date_start.isoformat()

        if date_end is not None:
            params["end_date"] = date_end.isoformat()

        return params

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
