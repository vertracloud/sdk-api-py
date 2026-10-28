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

    @property
    def issues(self) -> list[dict[str, Any]]:
        """Findings of a `DOCKERFILE_REFUSED` error: the objects in `details.issues`, as the API sent them
        (`{code, line}`). Tolerant on purpose: any other error, or a `details` of another shape, gives `[]`
        and never raises; entries that are not objects are skipped."""
        details = self.details
        if not isinstance(details, dict):
            return []
        raw = details.get("issues")
        if not isinstance(raw, list):
            return []
        return [item for item in raw if isinstance(item, dict)]

    def _details_for(self, code: str) -> dict[str, Any] | None:
        if self.code != code or not isinstance(self.details, dict):
            return None
        return self.details

    @property
    def manifest_issues(self) -> list[dict[str, Any]]:
        """Findings of a `TEMPLATE_MANIFEST_INVALID` error: the objects in `details.issues` (`{path, code, message}`).
        Tolerant like `issues`: any other error gives `[]`."""
        details = self._details_for("TEMPLATE_MANIFEST_INVALID")
        raw = details.get("issues") if details else None
        return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []

    @property
    def secret_files(self) -> list[str]:
        """Paths of a `TEMPLATE_SECRET_IN_SOURCE` error: the files of the code sent to become a template that hold
        a secret. Any other error gives `[]`."""
        details = self._details_for("TEMPLATE_SECRET_IN_SOURCE")
        raw = details.get("files") if details else None
        return [item for item in raw if isinstance(item, str)] if isinstance(raw, list) else []

    @property
    def update_blocked(self) -> dict[str, Any] | None:
        """Reason of a `TEMPLATE_UPDATE_BLOCKED` error (`{reason, details?}`); `None` for any other error."""
        return self._details_for("TEMPLATE_UPDATE_BLOCKED")

    @property
    def detach_action(self) -> str | None:
        """Action of a `TEMPLATE_DETACH_CONFIRMATION_REQUIRED` error (`files.write`, `deploy.code`,
        `deploy.github` or `commit`): repeat the call with `confirm_detach=True` to detach the app from its template.
        `None` for any other error."""
        details = self._details_for("TEMPLATE_DETACH_CONFIRMATION_REQUIRED")
        action = details.get("action") if details else None
        return action if isinstance(action, str) else None


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


class AppNotReadyError(Exception):
    """`apps.wait_until_ready` ended without a running app. `app` is the last payload seen
    (`None` on timeout before any reply). The cause of a `down` build is in `apps.logs`."""

    def __init__(self, message: str, *, code: str, app: Any = None) -> None:
        self.code = code
        self.app = app
        super().__init__(f"{code}: {message}")


class AppBuildFailedError(AppNotReadyError):
    """The build ended with the app `down`. `code` is the app's `last_build_error` (e.g.
    `INSTALL_OUT_OF_MEMORY`), or `APP_DOWN` when the API sent none."""


class WaitTimeoutError(AppNotReadyError):
    """`wait_until_ready` timed out while the app was still `building` (`code` is `WAIT_TIMEOUT`)."""


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
