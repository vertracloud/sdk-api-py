"""Typed Python client for the Vertra Cloud public API (`import vertracloud`)."""

from .client import VertraClient, __version__
from .errors import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ScopeDeniedError,
    ValidationError,
    VertraAPIError,
)
from .sse import SseEvent, SseStream
from .transport import Response, Transport, UrllibTransport

__all__ = [
    "VertraClient",
    "__version__",
    "VertraAPIError",
    "AuthenticationError",
    "ScopeDeniedError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "SseEvent",
    "SseStream",
    "Transport",
    "UrllibTransport",
    "Response",
]
