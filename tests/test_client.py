"""Tests for the base Client class."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from periodical_distiller.clients import (
    APIError,
    Client,
    ConnectionError,
    NotFoundError,
    RateLimitError,
)


class ConcreteClient(Client):
    """Concrete implementation of Client for testing."""

    def fetch(self, *args, **kwargs):
        return self.get("/test")


class TestClientConfiguration:
    """Tests for Client configuration."""

    def test_requires_base_url(self):
        """Client raises ValueError if base_url is missing."""
        with pytest.raises(ValueError, match="base_url"):
            ConcreteClient({})

    def test_base_url_from_config(self):
        """Client stores base_url from config."""
        client = ConcreteClient({"base_url": "https://api.example.com"})

        assert client.base_url == "https://api.example.com"

    def test_default_timeout(self):
        """Client has default timeout of 30 seconds."""
        client = ConcreteClient({"base_url": "https://api.example.com"})

        assert client.timeout == 30

    def test_custom_timeout(self):
        """Client accepts custom timeout."""
        client = ConcreteClient({"base_url": "https://api.example.com", "timeout": 60})

        assert client.timeout == 60

    def test_default_retry_attempts(self):
        """Client has default retry_attempts of 3."""
        client = ConcreteClient({"base_url": "https://api.example.com"})

        assert client.retry_attempts == 3

    def test_custom_retry_attempts(self):
        """Client accepts custom retry_attempts."""
        client = ConcreteClient({"base_url": "https://api.example.com", "retry_attempts": 5})

        assert client.retry_attempts == 5

    def test_default_retry_delay(self):
        """Client has default retry_delay of 1 second."""
        client = ConcreteClient({"base_url": "https://api.example.com"})

        assert client.retry_delay == 1

    def test_custom_retry_delay(self):
        """Client accepts custom retry_delay."""
        client = ConcreteClient({"base_url": "https://api.example.com", "retry_delay": 0.5})

        assert client.retry_delay == 0.5

    def test_default_headers(self):
        """Client has empty default headers."""
        client = ConcreteClient({"base_url": "https://api.example.com"})

        assert client.headers == {}

    def test_custom_headers(self):
        """Client accepts custom headers."""
        headers = {"Authorization": "Bearer token123"}
        client = ConcreteClient({"base_url": "https://api.example.com", "headers": headers})

        assert client.headers == headers


class TestClientLifecycle:
    """Tests for Client lifecycle management."""

    def test_lazy_client_initialization(self):
        """httpx.Client is not created until accessed."""
        client = ConcreteClient({"base_url": "https://api.example.com"})

        assert client._client is None

    def test_client_initialized_on_access(self):
        """httpx.Client is created when client property is accessed."""
        client = ConcreteClient({"base_url": "https://api.example.com"})

        _ = client.client

        assert client._client is not None
        assert isinstance(client._client, httpx.Client)

        client.close()

    def test_context_manager_closes_client(self):
        """Context manager closes the httpx client on exit."""
        with ConcreteClient({"base_url": "https://api.example.com"}) as client:
            _ = client.client
            assert client._client is not None

        assert client._client is None

    def test_close_when_not_initialized(self):
        """Calling close when client not initialized is safe."""
        client = ConcreteClient({"base_url": "https://api.example.com"})
        client.close()

        assert client._client is None


class TestClientErrorHandling:
    """Tests for Client error handling."""

    def test_404_raises_not_found_error(self):
        """404 response raises NotFoundError."""
        client = ConcreteClient({"base_url": "https://api.example.com"})
        response = MagicMock()
        response.is_success = False
        response.status_code = 404
        response.url = "https://api.example.com/test"

        with pytest.raises(NotFoundError) as exc_info:
            client._handle_response(response)

        assert exc_info.value.status_code == 404

    def test_429_raises_rate_limit_error(self):
        """429 response raises RateLimitError."""
        client = ConcreteClient({"base_url": "https://api.example.com"})
        response = MagicMock()
        response.is_success = False
        response.status_code = 429
        response.url = "https://api.example.com/test"

        with pytest.raises(RateLimitError) as exc_info:
            client._handle_response(response)

        assert exc_info.value.status_code == 429

    def test_500_raises_api_error(self):
        """5xx response raises APIError."""
        client = ConcreteClient({"base_url": "https://api.example.com"})
        response = MagicMock()
        response.is_success = False
        response.status_code = 500
        response.url = "https://api.example.com/test"

        with pytest.raises(APIError) as exc_info:
            client._handle_response(response)

        assert exc_info.value.status_code == 500

    def test_success_returns_response(self):
        """Successful response is returned as-is."""
        client = ConcreteClient({"base_url": "https://api.example.com"})
        response = MagicMock()
        response.is_success = True

        result = client._handle_response(response)

        assert result is response


class TestClientRetryLogic:
    """Tests for Client retry behavior."""

    @patch("periodical_distiller.clients.client.sleep")
    def test_retries_on_connection_error(self, mock_sleep):
        """Client retries on connection errors."""
        client = ConcreteClient({
            "base_url": "https://api.example.com",
            "retry_attempts": 3,
            "retry_delay": 0.1,
        })

        mock_http_client = MagicMock()
        mock_http_client.request.side_effect = httpx.ConnectError("Connection refused")
        client._client = mock_http_client

        with pytest.raises(ConnectionError) as exc_info:
            client.get("/test")

        assert "Connection failed after 3 attempts" in str(exc_info.value)
        assert mock_http_client.request.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("periodical_distiller.clients.client.sleep")
    def test_retries_on_timeout(self, mock_sleep):
        """Client retries on timeout errors."""
        client = ConcreteClient({
            "base_url": "https://api.example.com",
            "retry_attempts": 2,
            "retry_delay": 0.1,
        })

        mock_http_client = MagicMock()
        mock_http_client.request.side_effect = httpx.TimeoutException("Request timed out")
        client._client = mock_http_client

        with pytest.raises(ConnectionError):
            client.get("/test")

        assert mock_http_client.request.call_count == 2

    @patch("periodical_distiller.clients.client.sleep")
    def test_succeeds_after_retry(self, mock_sleep):
        """Client succeeds if retry works."""
        client = ConcreteClient({
            "base_url": "https://api.example.com",
            "retry_attempts": 3,
        })

        success_response = MagicMock()
        success_response.is_success = True

        mock_http_client = MagicMock()
        mock_http_client.request.side_effect = [
            httpx.ConnectError("Connection refused"),
            success_response,
        ]
        client._client = mock_http_client

        result = client.get("/test")

        assert result is success_response
        assert mock_http_client.request.call_count == 2

    def test_no_retry_on_api_error(self):
        """Client does not retry on API errors (non-transient)."""
        client = ConcreteClient({
            "base_url": "https://api.example.com",
            "retry_attempts": 3,
        })

        error_response = MagicMock()
        error_response.is_success = False
        error_response.status_code = 400
        error_response.url = "https://api.example.com/test"

        mock_http_client = MagicMock()
        mock_http_client.request.return_value = error_response
        client._client = mock_http_client

        with pytest.raises(APIError):
            client.get("/test")

        assert mock_http_client.request.call_count == 1


class TestClientAbstractMethods:
    """Tests for Client abstract methods."""

    def test_fetch_must_be_implemented(self):
        """Subclasses must implement fetch method."""

        class IncompleteClient(Client):
            pass

        with pytest.raises(TypeError, match="fetch"):
            IncompleteClient({"base_url": "https://api.example.com"})
