"""Base client for network requests."""

import logging
from abc import ABC, abstractmethod
from time import sleep
from typing import Any

import httpx

from .exceptions import (
    APIError,
    ConnectionError,
    NotFoundError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class Client(ABC):
    """Base class for network clients.

    Provides lazy-initialized httpx.Client with context manager support,
    configurable timeout, retries, and headers via dict config.

    Config keys:
        base_url (required): Base URL for all requests
        timeout: Request timeout in seconds (default: 30)
        retry_attempts: Number of retry attempts for transient failures (default: 3)
        retry_delay: Delay between retries in seconds (default: 1)
        headers: Additional headers to include in requests
    """

    def __init__(self, config: dict):
        if "base_url" not in config:
            raise ValueError("config must include 'base_url'")

        self._config = config
        self._client: httpx.Client | None = None

    @property
    def base_url(self) -> str:
        return str(self._config["base_url"])

    @property
    def timeout(self) -> float:
        return float(self._config.get("timeout", 30))

    @property
    def retry_attempts(self) -> int:
        return int(self._config.get("retry_attempts", 3))

    @property
    def retry_delay(self) -> float:
        return float(self._config.get("retry_delay", 1))

    @property
    def headers(self) -> dict[str, str]:
        return dict(self._config.get("headers", {}))

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialized httpx client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self.headers,
            )
        return self._client

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def _handle_response(self, response: httpx.Response) -> httpx.Response:
        """Map HTTP errors to exceptions.

        Args:
            response: The HTTP response to check

        Returns:
            The response if successful

        Raises:
            NotFoundError: For 404 responses
            RateLimitError: For 429 responses
            APIError: For other non-2xx responses
        """
        if response.is_success:
            return response

        status_code = response.status_code

        if status_code == 404:
            raise NotFoundError(f"Resource not found: {response.url}")
        elif status_code == 429:
            raise RateLimitError(f"Rate limit exceeded: {response.url}")
        else:
            raise APIError(
                f"API error {status_code}: {response.url}",
                status_code=status_code,
            )

    def _request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """Make a request with retry logic for transient failures.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: URL path (appended to base_url)
            **kwargs: Additional arguments passed to httpx.request

        Returns:
            The HTTP response

        Raises:
            ConnectionError: If all retry attempts fail due to network issues
            APIError: If the API returns a non-2xx response
        """
        last_exception: Exception | None = None

        for attempt in range(self.retry_attempts):
            try:
                response = self.client.request(method, path, **kwargs)
                return self._handle_response(response)
            except httpx.ConnectError as e:
                last_exception = e
                logger.warning(
                    f"Connection error (attempt {attempt + 1}/{self.retry_attempts}): {e}"
                )
                if attempt < self.retry_attempts - 1:
                    sleep(self.retry_delay)
            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(
                    f"Timeout (attempt {attempt + 1}/{self.retry_attempts}): {e}"
                )
                if attempt < self.retry_attempts - 1:
                    sleep(self.retry_delay)

        msg = f"Connection failed after {self.retry_attempts} attempts"
        raise ConnectionError(msg) from last_exception

    def get(self, path: str, **kwargs) -> httpx.Response:
        """Convenience method for GET requests.

        Args:
            path: URL path (appended to base_url)
            **kwargs: Additional arguments passed to httpx.request

        Returns:
            The HTTP response
        """
        return self._request("GET", path, **kwargs)

    @abstractmethod
    def fetch(self, *args, **kwargs) -> Any:
        """Fetch data from the API. Must be implemented by subclasses."""
        pass
