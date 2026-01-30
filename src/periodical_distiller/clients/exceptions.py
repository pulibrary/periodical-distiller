"""Custom exceptions for network clients."""


class ClientError(Exception):
    """Base exception for all client errors."""

    def __init__(self, message: str, *args, **kwargs):
        self.message = message
        super().__init__(message, *args, **kwargs)


class ConnectionError(ClientError):
    """Raised when a network connection fails."""

    pass


class APIError(ClientError):
    """Raised when the API returns a non-2xx response."""

    def __init__(self, message: str, status_code: int, *args, **kwargs):
        self.status_code = status_code
        super().__init__(message, *args, **kwargs)


class RateLimitError(APIError):
    """Raised when the API returns a 429 rate limit response."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)


class NotFoundError(APIError):
    """Raised when the API returns a 404 not found response."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class ValidationError(ClientError):
    """Raised when response data fails schema validation."""

    def __init__(self, message: str, errors: list | None = None, *args, **kwargs):
        self.errors = errors or []
        super().__init__(message, *args, **kwargs)
