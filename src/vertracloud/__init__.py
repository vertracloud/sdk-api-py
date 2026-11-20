"""Typed Python client for the Vertra Cloud public API (`import vertracloud`)."""

from . import errcodes
from .client import VertraClient, __version__
from .errors import (
    AppBuildFailedError,
    AppNotReadyError,
    AuthenticationError,
    DownloadIncompleteError,
    NotFoundError,
    RateLimitError,
    ScopeDeniedError,
    SnapshotJobError,
    SnapshotJobFailedError,
    SnapshotJobSkippedError,
    SnapshotJobTimeoutError,
    ValidationError,
    VertraAPIError,
    WaitTimeoutError,
)
from .resources.templates import TemplateDeployEventStream
from .sse import SseEvent, SseStream
from .transport import Response, Transport, UrllibTransport

__all__ = [
    "VertraClient",
    "__version__",
    "VertraAPIError",
    "AppNotReadyError",
    "AppBuildFailedError",
    "WaitTimeoutError",
    "SnapshotJobError",
    "SnapshotJobFailedError",
    "SnapshotJobSkippedError",
    "SnapshotJobTimeoutError",
    "AuthenticationError",
    "DownloadIncompleteError",
    "ScopeDeniedError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "SseEvent",
    "SseStream",
    "TemplateDeployEventStream",
    "errcodes",
    "Transport",
    "UrllibTransport",
    "Response",
]
