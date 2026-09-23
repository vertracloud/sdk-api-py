"""Fake transport for tests — never hits the real API. Records every call
(method, url, headers, body) and returns canned responses from a queue."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from vertracloud.transport import Response


@dataclass
class RecordedCall:
    method: str
    url: str
    headers: dict[str, str]
    body: bytes | None
    timeout: float
    stream: bool

    @property
    def path(self) -> str:
        return urlparse(self.url).path


@dataclass
class FakeTransport:
    calls: list[RecordedCall] = field(default_factory=list)
    _queue: list[Response] = field(default_factory=list)
    default_json: Any = field(default_factory=lambda: {"response": {"ok": True}})

    def queue(self, response: Response) -> None:
        self._queue.append(response)

    def queue_json(self, payload: Any, status: int = 200, headers: dict[str, str] | None = None) -> None:
        self._queue.append(Response(status=status, headers=headers or {}, body=json.dumps(payload).encode("utf-8")))

    def queue_error(
        self,
        status: int,
        code: str,
        *,
        message: str | None = None,
        details: Any = None,
        retry_after: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        body: dict[str, Any] = {"code": code}
        if message is not None:
            body["message"] = message
        if details is not None:
            body["details"] = details
        if retry_after is not None:
            body["retry_after"] = retry_after
        self._queue.append(Response(status=status, headers=headers or {}, body=json.dumps(body).encode("utf-8")))

    def queue_binary(self, data: bytes, status: int = 200, headers: dict[str, str] | None = None) -> None:
        self._queue.append(Response(status=status, headers=headers or {}, body=data))

    def queue_stream(self, lines: list[bytes], status: int = 200, headers: dict[str, str] | None = None) -> None:
        self._queue.append(Response(status=status, headers=headers or {}, stream=iter(lines)))

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
        self.calls.append(
            RecordedCall(method=method, url=url, headers=dict(headers), body=body, timeout=timeout, stream=stream)
        )
        if self._queue:
            return self._queue.pop(0)
        return Response(status=200, headers={}, body=json.dumps(self.default_json).encode("utf-8"))
