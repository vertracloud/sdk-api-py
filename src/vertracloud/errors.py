"""Typed SDK exceptions, derived from the API's error envelope.

Error envelope: `{code, message?, details?, retry_after?}`. The class is picked from the
HTTP status; `code` is always accessible on the exception. Never print the API key
here — `__repr__`/`__str__` only show status/code/message.
"""

from __future__ import annotations

from typing import Any


class VertraAPIError(Exception):
    """Generic API error. Base class for every typed SDK exception."""

    def __init__(
        self,
        message: str | None,
        *,
        status: int,
        code: str,
        details: Any = None,
    ) -> None:
        self.status = status
        self.code = code
        self.details = details
        super().__init__(message or code)

    def __str__(self) -> str:
        return f"{self.code} ({self.status}): {super().__str__()}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status={self.status!r}, code={self.code!r})"


class AuthenticationError(VertraAPIError):
    """401 — invalid key or user not found (`API_KEY_INVALID`, `USER_NOT_FOUND`)."""


class ScopeDeniedError(VertraAPIError):
    """403 — key missing the required scope or IP, a ban, or a WEBSITE_ONLY route."""


class NotFoundError(VertraAPIError):
    """404 — resource does not exist (`APP_NOT_FOUND`, `DATABASE_NOT_FOUND`, ...)."""


class ValidationError(VertraAPIError):
    """400/422 — invalid body, query, or path."""


class RateLimitError(VertraAPIError):
    """429 — per-minute limit or daily quota exceeded."""

    def __init__(
        self,
        message: str | None,
        *,
        status: int,
        code: str,
        details: Any = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message, status=status, code=code, details=details)
        self.retry_after = retry_after

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(status={self.status!r}, code={self.code!r}, retry_after={self.retry_after!r})"
        )


def error_from_response(status: int, body: dict[str, Any]) -> VertraAPIError:
    """Picks the class from the HTTP status; `code` comes from the error response body."""
    code = str(body.get("code") or "UNKNOWN_ERROR")
    message = body.get("message")
    details = body.get("details")
    if status == 401:
        return AuthenticationError(message, status=status, code=code, details=details)
    if status == 403:
        return ScopeDeniedError(message, status=status, code=code, details=details)
    if status == 404:
        return NotFoundError(message, status=status, code=code, details=details)
    if status in (400, 422):
        return ValidationError(message, status=status, code=code, details=details)
    if status == 429:
        retry_after = body.get("retry_after")
        try:
            retry_after = float(retry_after) if retry_after is not None else None
        except (TypeError, ValueError):
            retry_after = None
        return RateLimitError(message, status=status, code=code, details=details, retry_after=retry_after)
    return VertraAPIError(message, status=status, code=code, details=details)
