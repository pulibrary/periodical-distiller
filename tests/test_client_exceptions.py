"""Tests for client exception classes."""


from periodical_distiller.clients import (
    APIError,
    ClientError,
    ConnectionError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)


class TestClientError:
    """Tests for the base ClientError exception."""

    def test_instantiation_with_message(self):
        """ClientError stores the error message."""
        error = ClientError("Something went wrong")

        assert error.message == "Something went wrong"
        assert str(error) == "Something went wrong"

    def test_inheritance(self):
        """ClientError is an Exception."""
        error = ClientError("test")

        assert isinstance(error, Exception)


class TestConnectionError:
    """Tests for ConnectionError exception."""

    def test_instantiation(self):
        """ConnectionError stores the error message."""
        error = ConnectionError("Network unreachable")

        assert error.message == "Network unreachable"

    def test_inheritance(self):
        """ConnectionError inherits from ClientError."""
        error = ConnectionError("test")

        assert isinstance(error, ClientError)
        assert isinstance(error, Exception)


class TestAPIError:
    """Tests for APIError exception."""

    def test_instantiation_with_status_code(self):
        """APIError stores message and status code."""
        error = APIError("Server error", status_code=500)

        assert error.message == "Server error"
        assert error.status_code == 500

    def test_inheritance(self):
        """APIError inherits from ClientError."""
        error = APIError("test", status_code=500)

        assert isinstance(error, ClientError)


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_default_message(self):
        """RateLimitError has a default message."""
        error = RateLimitError()

        assert error.message == "Rate limit exceeded"
        assert error.status_code == 429

    def test_custom_message(self):
        """RateLimitError accepts custom message."""
        error = RateLimitError("Too many requests, retry after 60s")

        assert error.message == "Too many requests, retry after 60s"
        assert error.status_code == 429

    def test_inheritance(self):
        """RateLimitError inherits from APIError."""
        error = RateLimitError()

        assert isinstance(error, APIError)
        assert isinstance(error, ClientError)


class TestNotFoundError:
    """Tests for NotFoundError exception."""

    def test_default_message(self):
        """NotFoundError has a default message."""
        error = NotFoundError()

        assert error.message == "Resource not found"
        assert error.status_code == 404

    def test_custom_message(self):
        """NotFoundError accepts custom message."""
        error = NotFoundError("Article 12345 not found")

        assert error.message == "Article 12345 not found"
        assert error.status_code == 404

    def test_inheritance(self):
        """NotFoundError inherits from APIError."""
        error = NotFoundError()

        assert isinstance(error, APIError)
        assert isinstance(error, ClientError)


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_instantiation_with_message(self):
        """ValidationError stores message."""
        error = ValidationError("Invalid data")

        assert error.message == "Invalid data"
        assert error.errors == []

    def test_instantiation_with_errors(self):
        """ValidationError stores validation error details."""
        errors = ["field 'id' is required", "field 'name' must be a string"]
        error = ValidationError("Validation failed", errors=errors)

        assert error.message == "Validation failed"
        assert error.errors == errors
        assert len(error.errors) == 2

    def test_inheritance(self):
        """ValidationError inherits from ClientError."""
        error = ValidationError("test")

        assert isinstance(error, ClientError)
        assert isinstance(error, Exception)
