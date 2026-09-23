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
                "missing_dependencies": ["requests"],
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
        "missing_dependencies": ["requests"],
        "removed_directories": [],
    }


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
