"""Injectable HTTP transport. `VertraClient` only talks to the outside world through
`Transport`, which lets tests run without network (a fake transport) and lets the
default implementation be swapped out.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass, field
from email.message import Message
from typing import Any, Protocol
from urllib.parse import urlsplit


@dataclass
class Response:
    """Raw response from a call. `stream` is only set when requested (SSE lines, or byte chunks with `chunk_size`)."""

    status: int
    headers: dict[str, str]
    body: bytes = b""
    stream: Iterator[bytes] | None = None


class Transport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
        *,
        stream: bool = False,
        chunk_size: int | None = None,
    ) -> Response: ...


class _AuthStrippingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follows redirects but never forwards `Authorization` to another origin (scheme, host or port)."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: Message | dict[str, str],
        newurl: str,
    ) -> urllib.request.Request | None:
        new = super().redirect_request(req, fp, code, msg, headers, newurl)  # type: ignore[arg-type]
        if new is not None and _origin(req.full_url) != _origin(new.full_url):
            for name in [h for h in new.headers if h.lower() == "authorization"]:
                del new.headers[name]
            for name in [h for h in new.unredirected_hdrs if h.lower() == "authorization"]:
                del new.unredirected_hdrs[name]
        return new


def _origin(url: str) -> tuple[str, str, int | None]:
    parts = urlsplit(url)
    return (
        parts.scheme.lower(),
        (parts.hostname or "").lower(),
        parts.port or {"http": 80, "https": 443}.get(parts.scheme.lower()),
    )


_opener = urllib.request.build_opener(_AuthStrippingRedirectHandler)


class ChunkStream:
    """Byte chunks of an open response, read as the caller asks (nothing is buffered). `close()` is safe at any moment,
    even before the first chunk. `timeout` of the request applies to each read, so a stalled body raises."""

    def __init__(self, resp: Any, chunk_size: int) -> None:
        self._resp = resp
        self._chunk_size = chunk_size

    def __iter__(self) -> ChunkStream:
        return self

    def __next__(self) -> bytes:
        if self._resp is None:
            raise StopIteration
        try:
            chunk: bytes = self._resp.read(self._chunk_size)
        except BaseException:
            self.close()
            raise
        if not chunk:
            self.close()
            raise StopIteration
        return chunk

    def close(self) -> None:
        resp, self._resp = self._resp, None
        if resp is not None:
            resp.close()


@dataclass
class UrllibTransport:
    """Default implementation, pure stdlib (`urllib`) — zero runtime dependencies."""

    _last_raw: object = field(default=None, repr=False)

    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout: float,
        *,
        stream: bool = False,
        chunk_size: int | None = None,
    ) -> Response:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            resp = _opener.open(req, timeout=timeout)  # noqa: S310 - URL comes from the configured base_url
        except urllib.error.HTTPError as exc:
            data = exc.read()
            resp_headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
            return Response(status=exc.code, headers=resp_headers, body=data)

        resp_headers = {k.lower(): v for k, v in resp.headers.items()}
        if stream and chunk_size:
            return Response(status=resp.status, headers=resp_headers, stream=ChunkStream(resp, chunk_size))
        if stream:

            def iterator() -> Iterator[bytes]:
                try:
                    while True:
                        chunk = resp.readline()
                        if not chunk:
                            break
                        yield chunk
                finally:
                    resp.close()

            return Response(status=resp.status, headers=resp_headers, stream=iterator())

        try:
            data = resp.read()
        finally:
            resp.close()
        return Response(status=resp.status, headers=resp_headers, body=data)
