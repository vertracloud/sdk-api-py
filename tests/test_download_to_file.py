"""`download_to_file`/`download_stream` write the zip as it arrives, with constant memory, through a temporary file
next to the destination: a failure, a stall or a cancellation leaves no file at all."""

from __future__ import annotations

import hashlib
import resource
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from vertracloud import VertraClient

from .fake_transport import FakeTransport

ID = "11111111-1111-1111-1111-111111111111"
SNAP = "22222222-2222-2222-2222-222222222222"
MB = 1024 * 1024


def _rss_mb() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / MB if sys.platform == "darwin" else peak / 1024


def _chunk(index: int) -> bytes:
    return bytes([index % 251]) * MB


def _handler(chunks: int, *, stall_after: int | None = None, pause: float = 0.0) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(chunks * MB))
            self.end_headers()
            try:
                for index in range(chunks):
                    if stall_after is not None and index >= stall_after:
                        time.sleep(5)
                        return
                    self.wfile.write(_chunk(index))
                    if pause:
                        time.sleep(pause)
            except OSError:
                return

        def log_message(self, *args: Any) -> None:
            return

    return Handler


@contextmanager
def _server(handler: type[BaseHTTPRequestHandler]) -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_400_mb_reach_the_disk_with_constant_memory_and_an_identical_file(tmp_path: Path) -> None:
    total = 400
    expected = hashlib.sha256()
    for index in range(total):
        expected.update(_chunk(index))
    target = tmp_path / "snapshot.zip"
    before = _rss_mb()
    with _server(_handler(total)) as base_url:
        client = VertraClient(api_key="k", base_url=base_url)
        written = client.snapshots.download_to_file(ID, SNAP, "applications", target)
    assert written == total * MB
    assert target.stat().st_size == total * MB
    digest = hashlib.sha256()
    with target.open("rb") as f:
        while block := f.read(MB):
            digest.update(block)
    assert digest.hexdigest() == expected.hexdigest()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["snapshot.zip"]
    assert _rss_mb() - before < 120, f"peak RSS grew {_rss_mb() - before:.0f} MB for a {total} MB file"


def test_bytes_are_on_disk_before_the_response_ends(tmp_path: Path) -> None:
    seen: list[int] = []
    with _server(_handler(40, pause=0.01)) as base_url:
        client = VertraClient(api_key="k", base_url=base_url)
        stream = client.snapshots.download_stream(ID, SNAP, "applications")
        from vertracloud.client import write_stream_to_file

        def watching() -> Iterator[bytes]:
            for index, chunk in enumerate(stream):
                if index == 30:
                    seen.extend(p.stat().st_size for p in tmp_path.glob("*.part"))
                    assert not (tmp_path / "out.zip").exists()
                yield chunk

        write_stream_to_file(watching(), tmp_path / "out.zip")
    assert seen
    assert seen[0] >= 25 * MB


def test_a_download_that_stalls_leaves_no_file(tmp_path: Path) -> None:
    with _server(_handler(4, stall_after=2)) as base_url:
        client = VertraClient(api_key="k", base_url=base_url)
        started = time.monotonic()
        with pytest.raises((TimeoutError, OSError)):
            client.snapshots.download_to_file(ID, SNAP, "applications", tmp_path / "snapshot.zip", timeout=0.4)
        assert time.monotonic() - started < 4
    assert list(tmp_path.iterdir()) == []


def test_a_failure_while_writing_removes_the_temporary_file_and_closes_the_stream(tmp_path: Path) -> None:
    from vertracloud.client import write_stream_to_file

    closed: list[bool] = []

    class Chunks:
        def __init__(self) -> None:
            self.sent = 0

        def __iter__(self) -> Chunks:
            return self

        def __next__(self) -> bytes:
            self.sent += 1
            if self.sent == 3:
                raise KeyboardInterrupt
            return b"x" * 1024

        def close(self) -> None:
            closed.append(True)

    with pytest.raises(KeyboardInterrupt):
        write_stream_to_file(Chunks(), tmp_path / "snapshot.zip")  # type: ignore[arg-type]
    assert list(tmp_path.iterdir()) == []
    assert closed == [True]


def test_an_existing_file_is_replaced_only_at_the_end(tmp_path: Path) -> None:
    target = tmp_path / "snapshot.zip"
    target.write_bytes(b"old")
    transport = FakeTransport()
    transport.queue_binary(b"new-bytes")
    client = VertraClient(api_key="k", transport=transport)
    assert client.snapshots.download_to_file(ID, SNAP, "applications", target) == 9
    assert target.read_bytes() == b"new-bytes"
    assert transport.calls[0].stream is True
    assert transport.calls[0].chunk_size


def test_an_api_error_raises_the_typed_error_and_leaves_no_file(tmp_path: Path) -> None:
    from vertracloud.errors import NotFoundError

    transport = FakeTransport()
    transport.queue_error(404, "SNAPSHOT_NOT_FOUND")
    client = VertraClient(api_key="k", transport=transport)
    with pytest.raises(NotFoundError):
        client.snapshots.download_to_file(ID, SNAP, "applications", tmp_path / "snapshot.zip")
    assert list(tmp_path.iterdir()) == []


def test_apps_download_to_file_takes_the_snapshot_then_streams_it_to_disk(tmp_path: Path) -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": SNAP, "created_at": "2026-11-18T12:00:00.000Z"}}, status=201)
    transport.queue_binary(b"PK\x03\x04")
    client = VertraClient(api_key="k", transport=transport)
    target = tmp_path / "app.zip"
    assert client.apps.download_to_file(ID, target) == 4
    assert target.read_bytes() == b"PK\x03\x04"
    assert transport.calls[0].method == "POST"
    assert transport.calls[-1].path == f"/v1/users/{ID}/snapshots/{SNAP}/download"


def _cut_handler(declared: int, sent: int) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Length", str(declared))
            self.end_headers()
            try:
                self.wfile.write(b"z" * sent)
                self.wfile.flush()
            except OSError:
                return

        def log_message(self, *args: Any) -> None:
            return

    return Handler


def test_a_body_cut_before_the_content_length_is_an_error_and_leaves_no_file(tmp_path: Path) -> None:
    from vertracloud import DownloadIncompleteError

    target = tmp_path / "snapshot.zip"
    with _server(_cut_handler(4 * MB, 2 * MB)) as base_url:
        client = VertraClient(api_key="k", base_url=base_url)
        with pytest.raises(DownloadIncompleteError) as caught:
            client.snapshots.download_to_file(ID, SNAP, "applications", target)
    assert caught.value.expected == 4 * MB
    assert caught.value.received == 2 * MB
    assert list(tmp_path.iterdir()) == []


def test_a_cut_body_does_not_replace_an_existing_file(tmp_path: Path) -> None:
    from vertracloud import DownloadIncompleteError

    target = tmp_path / "snapshot.zip"
    target.write_bytes(b"old")
    with _server(_cut_handler(1000, 10)) as base_url:
        client = VertraClient(api_key="k", base_url=base_url)
        with pytest.raises(DownloadIncompleteError):
            client.snapshots.download_to_file(ID, SNAP, "applications", target)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["snapshot.zip"]
    assert target.read_bytes() == b"old"


def test_download_stream_also_raises_when_the_body_is_cut() -> None:
    from vertracloud import DownloadIncompleteError

    with _server(_cut_handler(1000, 10)) as base_url:
        client = VertraClient(api_key="k", base_url=base_url)
        stream = client.snapshots.download_stream(ID, SNAP, "applications")
        with pytest.raises(DownloadIncompleteError):
            b"".join(stream)


def test_a_complete_body_with_content_length_is_accepted_and_a_missing_header_is_not_checked(tmp_path: Path) -> None:
    from vertracloud.transport import Response

    transport = FakeTransport()
    transport.queue(Response(status=200, headers={"content-length": "4"}, body=b"PK\x03\x04"))
    client = VertraClient(api_key="k", transport=transport)
    assert client.snapshots.download_to_file(ID, SNAP, "applications", tmp_path / "a.zip") == 4
    transport.queue(Response(status=200, headers={}, body=b"PK\x03\x04"))
    assert client.snapshots.download_to_file(ID, SNAP, "applications", tmp_path / "b.zip") == 4


WS = "33333333-3333-3333-3333-333333333333"


def _queue_app_download(transport: FakeTransport) -> None:
    transport.queue_json({"response": {"job_id": "44444444-4444-4444-4444-444444444444"}}, status=202)
    transport.queue_json({"response": {"id": "j", "kind": "snapshot", "status": "ready", "snapshot_id": SNAP}})
    transport.queue_json({"response": [{"id": SNAP, "created_at": "2026-11-18T12:00:00.000Z"}]})
    transport.queue_binary(b"PK\x03\x04")


@pytest.mark.parametrize("method", ["download", "download_stream", "download_to_file"])
def test_apps_download_sends_the_workspace_on_every_call_of_the_flow(tmp_path: Path, method: str) -> None:
    transport = FakeTransport()
    _queue_app_download(transport)
    client = VertraClient(api_key="k", transport=transport)
    if method == "download_to_file":
        client.apps.download_to_file(ID, tmp_path / "a.zip", workspace_id=WS, interval=0)
    else:
        result = getattr(client.apps, method)(ID, workspace_id=WS, interval=0)
        if method == "download_stream":
            b"".join(result)
    assert len(transport.calls) == 4
    assert [c.method for c in transport.calls] == ["POST", "GET", "GET", "GET"]
    for call in transport.calls:
        assert f"workspace_id={WS}" in call.url, call.url


def test_snapshot_calls_send_the_workspace_when_given_and_omit_it_otherwise(tmp_path: Path) -> None:
    transport = FakeTransport()
    client = VertraClient(api_key="k", transport=transport)
    job = "44444444-4444-4444-4444-444444444444"
    client.snapshots.list(ID, "applications", workspace_id=WS)
    client.snapshots.create(ID, "applications", workspace_id=WS)
    client.snapshots.restore(ID, SNAP, "applications", workspace_id=WS)
    client.snapshot_jobs.list(ID, "applications", workspace_id=WS)
    client.snapshot_jobs.get(ID, job, "applications", workspace_id=WS)
    transport.queue_binary(b"PK")
    client.snapshots.download(ID, SNAP, "applications", workspace_id=WS)
    transport.queue_binary(b"PK")
    client.snapshots.download_to_file(ID, SNAP, "applications", tmp_path / "s.zip", workspace_id=WS)
    assert len(transport.calls) == 7
    for call in transport.calls:
        assert f"workspace_id={WS}" in call.url, call.url
    client.snapshots.list(ID, "applications")
    assert "workspace_id" not in transport.calls[-1].url
