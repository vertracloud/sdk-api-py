"""Central HTTP client. Every `resources/*.py` calls into `VertraClient` — no
resource method builds a URL, sets a header, or handles errors on its own.
"""

from __future__ import annotations

import json
import mimetypes
import uuid
from collections.abc import Iterable
from typing import Any
from urllib.parse import quote, urlencode

from .errors import error_from_response
from .sse import SseStream
from .transport import Response, Transport, UrllibTransport
from .types import JsonValue

__version__ = "0.1.1"  # x-release-please-version

DEFAULT_BASE_URL = "https://api.vertracloud.app"
DEFAULT_TIMEOUT = 30.0
# Download/upload/create for an app may involve a large zip file, so the timeout is longer.
LARGE_PAYLOAD_TIMEOUT = 120.0


def encode_path_param(value: str) -> str:
    """`quote(safe="")` — a path param never lets `/`, `?`, etc. leak into the URL structure."""
    return quote(str(value), safe="")


class MultipartField:
    """One part of a multipart body: plain text, or a file (with filename/content-type)."""

    __slots__ = ("name", "value", "filename", "content_type")

    def __init__(
        self,
        name: str,
        value: str | bytes,
        *,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> None:
        self.name = name
        self.value = value
        self.filename = filename
        self.content_type = content_type


def _build_multipart(fields: Iterable[MultipartField]) -> tuple[bytes, str]:
    boundary = f"----vertracloud-{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for field in fields:
        disposition = f'form-data; name="{field.name}"'
        if field.filename:
            disposition += f'; filename="{field.filename}"'
        header = f"--{boundary}\r\nContent-Disposition: {disposition}\r\n"
        content_type = field.content_type
        if content_type is None and field.filename:
            content_type = mimetypes.guess_type(field.filename)[0] or "application/octet-stream"
        if content_type:
            header += f"Content-Type: {content_type}\r\n"
        header += "\r\n"
        body = field.value if isinstance(field.value, bytes) else field.value.encode("utf-8")
        parts.append(header.encode("utf-8") + body + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


class VertraClient:
    """Client for the Vertra Cloud public API.

    Args:
        api_key: the user's API key (`Authorization: Bearer <key>`).
        base_url: defaults to `https://api.vertracloud.app`.
        timeout: seconds, defaults to 30. Can be overridden per call (download/upload/create).
        user_agent: defaults to `vertracloud-sdk-py/<version>`.
        transport: injectable `Transport` implementation (tests use a fake one).
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str | None = None,
        transport: Transport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.user_agent = user_agent or f"vertracloud-sdk-py/{__version__}"
        self.transport: Transport = transport or UrllibTransport()

        # Resources are imported here to avoid an import cycle at module top level.
        from .resources.account import AccountResource
        from .resources.apps import AppsResource
        from .resources.billing import BillingResource
        from .resources.databases import DatabasesResource
        from .resources.snapshots import SnapshotsResource
        from .resources.workspaces import WorkspacesResource

        self.apps = AppsResource(self)
        self.databases = DatabasesResource(self)
        self.snapshots = SnapshotsResource(self)
        self.account = AccountResource(self)
        self.workspaces = WorkspacesResource(self)
        self.billing = BillingResource(self)

    def __repr__(self) -> str:
        return f"VertraClient(base_url={self.base_url!r})"

    # -- HTTP core -------------------------------------------------------

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    def _url(self, path: str, query: dict[str, Any] | None = None) -> str:
        url = f"{self.base_url}{path}"
        if query:
            clean = {
                k: ("true" if v is True else "false" if v is False else v) for k, v in query.items() if v is not None
            }
            if clean:
                url += f"?{urlencode(clean)}"
        return url

    def request_json(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        json_body: Any = None,
        timeout: float | None = None,
    ) -> JsonValue:
        """Standard JSON call: sends `json_body` (if given), unwraps `{response}`."""
        headers = self._headers({"Content-Type": "application/json"} if json_body is not None else None)
        body = json.dumps(json_body).encode("utf-8") if json_body is not None else None
        resp = self.transport.request(method, self._url(path, query), headers, body, timeout or self.timeout)
        return self._unwrap(resp)

    def request_multipart(
        self,
        method: str,
        path: str,
        *,
        fields: list[MultipartField],
        query: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> JsonValue:
        body, boundary = _build_multipart(fields)
        headers = self._headers({"Content-Type": f"multipart/form-data; boundary={boundary}"})
        resp = self.transport.request(method, self._url(path, query), headers, body, timeout or self.timeout)
        return self._unwrap(resp)

    def request_binary(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """Binary downloads (app/snapshot zip, certificate). No JSON envelope."""
        headers = self._headers({"Accept": "*/*"})
        resp = self.transport.request(method, self._url(path, query), headers, None, timeout or self.timeout)
        if resp.status >= 400:
            self._raise_for_error(resp)
        return resp.body

    def request_sse(
        self,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> SseStream:
        """`GET /v1/apps/:id/realtime` — the only SSE route in the catalog."""
        headers = self._headers({"Accept": "text/event-stream"})
        resp = self.transport.request(
            "GET", self._url(path, query), headers, None, timeout or self.timeout, stream=True
        )
        if resp.status >= 400:
            self._raise_for_error(resp)
        if resp.stream is None:
            raise VertraClientError("Transport did not return a stream for an SSE request")
        return SseStream(resp.stream)

    # -- envelope --------------------------------------------------------

    def _unwrap(self, resp: Response) -> JsonValue:
        if resp.status >= 400:
            self._raise_for_error(resp)
        if not resp.body:
            return {}
        payload: Any = json.loads(resp.body)
        if isinstance(payload, dict) and "response" in payload:
            return payload["response"]
        return payload

    def _raise_for_error(self, resp: Response) -> None:
        try:
            payload = json.loads(resp.body) if resp.body else {}
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        if "retry_after" not in payload:
            retry_after_header = resp.headers.get("retry-after")
            if retry_after_header is not None:
                payload = {**payload, "retry_after": retry_after_header}
        raise error_from_response(resp.status, payload)


class VertraClientError(Exception):
    """Client usage error (not from the API), such as a misbehaving transport."""
