"""Injectable HTTP transport. `VertraClient` only talks to the outside world through
`Transport`, which lets tests run without network (a fake transport) and lets the
default implementation be swapped out.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Response:
    """Raw response from a call. `stream` is only set when requested (SSE)."""

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
    ) -> Response: ...


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
    ) -> Response:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)  # noqa: S310 - URL comes from the configured base_url
        except urllib.error.HTTPError as exc:
            data = exc.read()
            resp_headers = {k.lower(): v for k, v in exc.headers.items()} if exc.headers else {}
            return Response(status=exc.code, headers=resp_headers, body=data)

        resp_headers = {k.lower(): v for k, v in resp.headers.items()}
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
