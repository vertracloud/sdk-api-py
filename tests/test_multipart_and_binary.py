"""Multipart (create app / file upload) and binary responses (download/certificate)."""

from __future__ import annotations

import pytest

from vertracloud import VertraClient
from vertracloud.errors import NotFoundError

from .fake_transport import FakeTransport


def test_create_app_multipart_field_is_file_with_zip_bytes() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": "app-1"}})
    client = VertraClient(api_key="k", transport=transport)
    client.apps.create({"name": "myapp", "main": "index.js", "version": "18"}, file=b"PK\x03\x04zip-bytes")

    call = transport.calls[0]
    assert call.method == "POST"
    content_type = call.headers["Content-Type"]
    assert content_type.startswith("multipart/form-data; boundary=")
    body = call.body or b""
    assert b'name="file"' in body
    assert b"PK\x03\x04zip-bytes" in body
    assert b'name="name"' in body
    assert b"myapp" in body


def test_create_app_with_snapshot_id_has_no_file_field() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": "app-1"}})
    client = VertraClient(api_key="k", transport=transport)
    client.apps.create({"name": "myapp", "snapshot_id": "11111111-1111-1111-1111-111111111111"})
    body = transport.calls[0].body or b""
    assert b'name="file"' not in body
    assert b"snapshot_id" in body


def test_upload_file_multipart_field_name_is_file() -> None:
    transport = FakeTransport()
    transport.queue_json(
        {
            "response": {
                "app_id": "app-1",
                "updated_at": "2026-09-22T12:00:00.000Z",
                "removed_directories": [],
            }
        }
    )
    client = VertraClient(api_key="k", transport=transport)
    result = client.apps.files.upload("app-1", file=b"print(1)", filename="a.py", restart=True)
    body = transport.calls[0].body or b""
    assert b'name="file"; filename="a.py"' in body
    assert b"print(1)" in body
    assert "restart=true" in transport.calls[0].url
    assert result == {
        "app_id": "app-1",
        "updated_at": "2026-09-22T12:00:00.000Z",
        "removed_directories": [],
    }


def test_upload_file_message_is_a_text_part_and_optional() -> None:
    transport = FakeTransport()
    client = VertraClient(api_key="k", transport=transport)
    client.apps.files.upload("app-1", file=b"x", filename="a.py", message="fix login")
    client.apps.files.upload("app-1", file=b"x", filename="a.py")
    with_msg = transport.calls[0].body or b""
    without = transport.calls[1].body or b""
    assert b'name="message"\r\n\r\nfix login' in with_msg
    assert b'name="message"' not in without


def test_download_returns_raw_bytes_not_json() -> None:
    transport = FakeTransport()
    transport.queue_binary(b"\x50\x4b\x03\x04fake-zip")
    client = VertraClient(api_key="k", transport=transport)
    data = client.apps.download("app-1")
    assert data == b"\x50\x4b\x03\x04fake-zip"


def test_certificate_get_is_json_envelope_not_binary() -> None:
    """The certificate comes in the normal JSON envelope with crt/key/pem — not bytes — only
    `apps.download` and `snapshots.download` are binary in the catalog."""
    transport = FakeTransport()
    transport.queue_json(
        {
            "response": {
                "crt": "-----BEGIN CERTIFICATE-----\nfake-crt\n-----END CERTIFICATE-----",
                "key": "-----BEGIN PRIVATE KEY-----\nfake-key\n-----END PRIVATE KEY-----",
                "pem": "-----BEGIN CERTIFICATE-----\nfake-pem\n-----END CERTIFICATE-----",
            }
        }
    )
    client = VertraClient(api_key="k", transport=transport)
    cert = client.databases.credentials.certificate.get("db-1")
    assert isinstance(cert, dict)
    assert cert["crt"].startswith("-----BEGIN CERTIFICATE-----")
    assert "key" in cert
    assert "pem" in cert
    call = transport.calls[0]
    assert call.headers["Accept"] == "application/json"


def test_certificate_get_raises_typed_error_on_404() -> None:
    transport = FakeTransport()
    transport.queue_error(404, "DATABASE_NOT_FOUND")
    client = VertraClient(api_key="k", transport=transport)
    with pytest.raises(NotFoundError):
        client.databases.credentials.certificate.get("db-1")


def test_snapshot_download_returns_bytes() -> None:
    transport = FakeTransport()
    transport.queue_binary(b"zip-content")
    client = VertraClient(api_key="k", transport=transport)
    assert client.snapshots.download("user-1", "snap-1", "applications") == b"zip-content"


def _app(status: str) -> dict:
    return {"response": {"id": "app-1", "status": status}}


def test_wait_until_ready_returns_app_when_up() -> None:
    from vertracloud import VertraClient

    transport = FakeTransport()
    transport.queue_json(_app("building"))
    transport.queue_json(_app("up"))
    client = VertraClient(api_key="k", transport=transport)
    assert client.apps.wait_until_ready("app-1", interval=0)["status"] == "up"
    assert len(transport.calls) == 2


def test_wait_until_ready_raises_on_down_and_timeout() -> None:
    from vertracloud import AppBuildFailedError, VertraClient, WaitTimeoutError

    transport = FakeTransport()
    transport.queue_json(_app("down"))
    client = VertraClient(api_key="k", transport=transport)
    with pytest.raises(AppBuildFailedError) as down:
        client.apps.wait_until_ready("app-1", interval=0)
    assert down.value.code == "APP_DOWN"

    transport.queue_json({"response": {"id": "app-1", "status": "down", "last_build_error": "INSTALL_OUT_OF_MEMORY"}})
    with pytest.raises(AppBuildFailedError) as oom:
        client.apps.wait_until_ready("app-1", interval=0)
    assert oom.value.code == "INSTALL_OUT_OF_MEMORY"

    transport.default_json = _app("building")
    with pytest.raises(WaitTimeoutError) as slow:
        client.apps.wait_until_ready("app-1", timeout=0, interval=0)
    assert slow.value.code == "WAIT_TIMEOUT"


def _parse_parts(body: bytes, boundary: str) -> list[tuple[str, str | None, bytes]]:
    from email.parser import BytesParser
    from email.policy import HTTP

    raw = b"Content-Type: multipart/form-data; boundary=" + boundary.encode() + b"\r\n\r\n" + body
    msg = BytesParser(policy=HTTP).parsebytes(raw)
    out = []
    for part in msg.iter_parts():
        out.append(
            (part.get_param("name", header="content-disposition"), part.get_filename(), part.get_payload(decode=True))
        )
    return out


def test_multipart_filename_with_quote_and_semicolon_does_not_alter_parameters() -> None:
    from vertracloud.client import MultipartField, _build_multipart

    evil = 'a"; name="admin"; x=".zip'
    body, boundary = _build_multipart([MultipartField("file", b"data", filename=evil)])
    parts = _parse_parts(body, boundary)
    assert len(parts) == 1
    assert parts[0][0] == "file"
    assert parts[0][1] == evil
    assert b'filename="a\\"; name=\\"admin\\"' in body


def test_multipart_backslash_is_escaped() -> None:
    from vertracloud.client import MultipartField, _build_multipart

    body, _ = _build_multipart([MultipartField("file", b"d", filename="a\\b.zip")])
    assert b'filename="a\\\\b.zip"' in body


@pytest.mark.parametrize("bad", ["a\r\nX-Injected: 1.zip", "a\nb.zip", "a\rb.zip"])
def test_multipart_rejects_crlf_in_filename_and_field_name(bad: str) -> None:
    from vertracloud.client import MultipartField, _build_multipart

    with pytest.raises(ValueError, match="CR/LF"):
        _build_multipart([MultipartField("file", b"d", filename=bad)])
    with pytest.raises(ValueError, match="CR/LF"):
        _build_multipart([MultipartField(bad, "v")])
