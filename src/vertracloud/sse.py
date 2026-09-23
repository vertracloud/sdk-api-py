"""Server-Sent Events parser for `apps.realtime` (the only SSE route in the catalog).

Wire format: `event: <name>` and `data: <text>` lines per event, terminated by a blank
line (the SSE spec). Events seen: `logs`, `system`, `heartbeat`. No automatic reconnection
is implemented — closing the stream is the caller's responsibility, via `close()` or by
breaking out of the `for` loop.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class SseEvent:
    event: str
    data: str
    id: str | None = None


class SseStream:
    """Synchronous iterable over a stream of SSE lines, with `close()` to cancel."""

    def __init__(self, lines: Iterator[bytes]) -> None:
        self._lines = lines
        self._closed = False

    def close(self) -> None:
        self._closed = True
        close = getattr(self._lines, "close", None)
        if callable(close):
            close()

    def __iter__(self) -> Iterator[SseEvent]:
        event_type = "message"
        data_parts: list[str] = []
        event_id: str | None = None
        for raw in self._lines:
            if self._closed:
                return
            line = raw.decode("utf-8", errors="replace").rstrip("\n").rstrip("\r")
            if line == "":
                if data_parts:
                    yield SseEvent(event=event_type, data="\n".join(data_parts), id=event_id)
                event_type = "message"
                data_parts = []
                continue
            if line.startswith(":"):
                continue  # comment/keep-alive
            if ":" in line:
                field, _, value = line.partition(":")
                if value.startswith(" "):
                    value = value[1:]
            else:
                field, value = line, ""
            if field == "event":
                event_type = value
            elif field == "data":
                data_parts.append(value)
            elif field == "id":
                event_id = value
            # `retry` is ignored: no automatic reconnection in v1.
        if data_parts and not self._closed:
            yield SseEvent(event=event_type, data="\n".join(data_parts), id=event_id)
