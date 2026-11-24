"""SSE parser for `apps.realtime`: events, cancellation (`close()`), and passed-through timeout."""

from __future__ import annotations

import pytest

from vertracloud import VertraClient
from vertracloud.sse import SseStream

from .fake_transport import FakeTransport


def test_parses_event_and_data_lines() -> None:
    lines = [
        b"event: logs\n",
        b"data: hello world\n",
        b"\n",
        b"event: system\n",
        b"data: heartbeat\n",
        b"\n",
    ]
    events = list(SseStream(iter(lines)))
    assert [(e.event, e.data) for e in events] == [("logs", "hello world"), ("system", "heartbeat")]


def test_multiline_data_is_joined_with_newline() -> None:
    lines = [b"event: logs\n", b"data: line1\n", b"data: line2\n", b"\n"]
    events = list(SseStream(iter(lines)))
    assert events[0].data == "line1\nline2"


def test_comment_lines_are_ignored() -> None:
    lines = [b": keep-alive\n", b"event: system\n", b"data: ok\n", b"\n"]
    events = list(SseStream(iter(lines)))
    assert [(e.event, e.data) for e in events] == [("system", "ok")]


def test_default_event_type_is_message() -> None:
    lines = [b"data: no-event-field\n", b"\n"]
    events = list(SseStream(iter(lines)))
    assert events[0].event == "message"


def test_trailing_event_without_final_blank_line_is_still_yielded() -> None:
    lines = [b"event: logs\n", b"data: last\n"]
    events = list(SseStream(iter(lines)))
    assert [(e.event, e.data) for e in events] == [("logs", "last")]


def test_close_stops_iteration_and_calls_underlying_close() -> None:
    closed = {"value": False}

    class InfiniteLines:
        """Emulates an open connection: there is always one more line, it never ends on its own."""

        def __init__(self) -> None:
            self._script = [b"event: heartbeat\n", b"data: x\n", b"\n"]
            self._i = 0

        def __iter__(self):
            return self

        def __next__(self):
            line = self._script[self._i % len(self._script)]
            self._i += 1
            return line

        def close(self):
            closed["value"] = True

    stream = SseStream(InfiniteLines())
    it = iter(stream)
    first = next(it)
    assert first.event == "heartbeat"
    assert first.data == "x"
    stream.close()
    assert closed["value"] is True
    remaining = list(it)
    assert remaining == []


def test_realtime_request_passes_since_and_timeout_to_transport() -> None:
    transport = FakeTransport()
    transport.queue_stream([b"event: system\n", b"data: Connected\n", b"\n"])
    client = VertraClient(api_key="k", transport=transport)
    stream = client.apps.realtime("app-1", since=1000, timeout=2.5)
    events = list(stream)
    assert events[0].data == "Connected"
    call = transport.calls[0]
    assert call.timeout == 2.5
    assert "since=1000" in call.url
    assert call.headers["Accept"] == "text/event-stream"


def test_realtime_sends_metrics_true_only_when_asked() -> None:
    transport = FakeTransport()
    transport.queue_stream([b"event: heartbeat\n", b"data: \n", b"\n"])
    transport.queue_stream([b"event: heartbeat\n", b"data: \n", b"\n"])
    client = VertraClient(api_key="k", transport=transport)
    list(client.apps.realtime("app-1", metrics=True))
    list(client.apps.realtime("app-1"))
    assert "metrics=true" in transport.calls[0].url
    assert "metrics" not in transport.calls[1].url


def test_next_logs_and_metrics_events_are_delivered_and_metrics_parse() -> None:
    payload = (
        b'{"at":"2026-11-24T12:00:00.000Z","cpu_percent":12.5,"cpu_cores":0.25,"memory_bytes":104857600,'
        b'"memory_limit_bytes":null,"net_rx_bps":10.5,"net_tx_bps":20,"net_rx_bytes":1000,"net_tx_bytes":2000}'
    )
    stream = SseStream(
        iter(
            [
                b"event: next_logs\n",
                b"data: installing\n",
                b"\n",
                b"event: metrics\n",
                b"data: " + payload + b"\n",
                b"\n",
            ]
        )
    )
    logs, metrics = list(stream)
    assert logs.event == "next_logs"
    assert logs.data == "installing"
    live = metrics.live_metrics()
    assert live["cpu_percent"] == 12.5
    assert live["memory_limit_bytes"] is None
    assert live["net_tx_bytes"] == 2000
    with pytest.raises(ValueError):
        logs.live_metrics()
