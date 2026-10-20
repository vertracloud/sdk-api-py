from __future__ import annotations

import http.server
import threading
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from vertracloud.transport import UrllibTransport, _AuthStrippingRedirectHandler


class _Recorder(http.server.BaseHTTPRequestHandler):
    seen: list[str | None] = []
    location: str | None = None

    def do_GET(self) -> None:
        type(self).seen.append(self.headers.get("Authorization"))
        if type(self).location:
            self.send_response(302)
            self.send_header("Location", type(self).location or "")
            self.end_headers()
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, *args: object) -> None:
        pass


def _handler_class(location: str | None) -> type[_Recorder]:
    return type("H", (_Recorder,), {"seen": [], "location": location})


@contextmanager
def _serve(cls: type[_Recorder]) -> Iterator[int]:
    srv = http.server.HTTPServer(("127.0.0.1", 0), cls)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv.server_address[1]
    finally:
        srv.shutdown()
        srv.server_close()


def _get(url: str) -> int:
    return UrllibTransport().request("GET", url, {"Authorization": "Bearer SECRET"}, None, 5).status


def test_redirect_to_another_host_drops_authorization() -> None:
    target = _handler_class(None)
    with _serve(target) as target_port:
        origin = _handler_class(f"http://localhost:{target_port}/v1/x")
        with _serve(origin) as origin_port:
            assert _get(f"http://127.0.0.1:{origin_port}/v1/apps/abc") == 200
    assert origin.seen == ["Bearer SECRET"]
    assert target.seen == [None]


def test_redirect_to_another_port_drops_authorization() -> None:
    target = _handler_class(None)
    with _serve(target) as target_port:
        origin = _handler_class(f"http://127.0.0.1:{target_port}/v1/x")
        with _serve(origin) as origin_port:
            assert _get(f"http://127.0.0.1:{origin_port}/v1/apps/abc") == 200
    assert target.seen == [None]


def test_plain_request_sends_authorization() -> None:
    origin = _handler_class(None)
    with _serve(origin) as port:
        assert _get(f"http://127.0.0.1:{port}/v1/a") == 200
    assert origin.seen == ["Bearer SECRET"]


@pytest.mark.parametrize(
    ("from_url", "to_url", "kept"),
    [
        ("https://api.example.com/a", "http://api.example.com/b", False),
        ("https://api.example.com/a", "https://other.example.com/b", False),
        ("https://api.example.com/a", "https://api.example.com:8443/b", False),
        ("https://api.example.com/a", "https://API.example.com/b", True),
        ("https://api.example.com/a", "https://api.example.com/b", True),
    ],
)
def test_handler_strips_authorization_only_when_origin_changes(from_url: str, to_url: str, kept: bool) -> None:
    req = urllib.request.Request(from_url, headers={"Authorization": "Bearer SECRET", "Accept": "application/json"})
    new = _AuthStrippingRedirectHandler().redirect_request(req, None, 302, "Found", {}, to_url)  # type: ignore[arg-type]
    assert new is not None
    assert new.has_header("Authorization") is kept
    assert new.get_header("Accept") == "application/json"
