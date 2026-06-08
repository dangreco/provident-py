from __future__ import annotations

import httpx


class ProvidentError(Exception):
    """Base exception for all Provident client errors."""


class ProvidentAPIError(ProvidentError):
    """Raised when the Provident API returns an error response."""

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        headers: httpx.Headers | None = None,
        body: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.headers = headers
        self.body = body
        super().__init__(message)

    def __str__(self) -> str:
        return f"HTTP {self.status_code}: {self.message}"


class ProvidentAuthenticationError(ProvidentAPIError):
    """Raised when authentication with the Provident API fails."""


class ProvidentNotFoundError(ProvidentAPIError):
    """Raised when the requested resource is not found."""


class ProvidentRateLimitError(ProvidentAPIError):
    """Raised when the API rate limit is exceeded."""

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        retry_after: float | None = None,
        headers: httpx.Headers | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(status_code, message, headers=headers, body=body)
        self.retry_after = retry_after


class ProvidentServerError(ProvidentAPIError):
    """Raised when the Provident API returns a 5xx error."""

    def __init__(
        self,
        status_code: int,
        message: str,
        *,
        stack_trace: str | None = None,
        exception_type: str | None = None,
        headers: httpx.Headers | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(status_code, message, headers=headers, body=body)
        self.stack_trace = stack_trace
        self.exception_type = exception_type


class ProvidentConnectionError(ProvidentError):
    """Raised when a connection to the Provident API fails."""
