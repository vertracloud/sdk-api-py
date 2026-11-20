"""`snapshots.download` has no total deadline: `timeout` is per socket operation, so a zip that keeps arriving slowly
completes and one that stalls halfway fails."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from vertracloud import VertraClient

ID = "11111111-1111-1111-1111-111111111111"
SNAP = "22222222-2222-2222-2222-222222222222"


def _handler(chunks: int, pause: float, stall: bool) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str((chunks + (1 if stall else 0)) * 4))
            self.end_headers()
            try:
                for _ in range(chunks):
                    self.wfile.write(b"zip!")
                    self.wfile.flush()
                    time.sleep(pause)
                if stall:
                    time.sleep(5)
            except OSError:
                return

        def log_message(self, *args: Any) -> None:
            return

    return Handler


@contextmanager
def _server(chunks: int, pause: float, stall: bool = False) -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(chunks, pause, stall))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_a_download_slower_than_the_timeout_in_total_still_completes() -> None:
    with _server(chunks=8, pause=0.15) as base_url:
        client = VertraClient(api_key="k", base_url=base_url)
        started = time.monotonic()
        data = client.snapshots.download(ID, SNAP, "applications", timeout=0.6)
        assert time.monotonic() - started > 0.6
    assert data == b"zip!" * 8


def test_a_download_that_stalls_halfway_fails_after_the_inactivity_period() -> None:
    with _server(chunks=2, pause=0.05, stall=True) as base_url:
        client = VertraClient(api_key="k", base_url=base_url)
        started = time.monotonic()
        with pytest.raises((TimeoutError, OSError)):
            client.snapshots.download(ID, SNAP, "applications", timeout=0.5)
        assert time.monotonic() - started < 3
