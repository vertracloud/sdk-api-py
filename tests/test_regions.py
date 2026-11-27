"""The region field on the create calls, and the region error codes."""

from __future__ import annotations

import json

from vertracloud import VertraClient, errcodes

from .fake_transport import FakeTransport

ID = "11111111-1111-1111-1111-111111111111"


def _client(transport: FakeTransport) -> VertraClient:
    return VertraClient(api_key="secret-key", transport=transport)


def test_apps_create_sends_region_as_text_parts() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": ID}}, 201)
    _client(transport).apps.create({"name": "x", "region": "sp"}, file=b"zip")
    body = transport.calls[0].body
    assert b'name="region"\r\n\r\nsp\r\n' in body


def test_apps_create_omits_region_when_not_given() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": ID}}, 201)
    _client(transport).apps.create({"name": "x"}, file=b"zip")
    body = transport.calls[0].body
    assert b'name="region"' not in body
    assert b'name="node"' not in body


def test_apps_create_from_image_and_databases_create_send_region_in_json() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": ID}}, 202)
    client = _client(transport)
    client.apps.create_from_image({"image_id": ID, "name": "x", "memory": 512, "web": False, "region": "ny"})
    transport.queue_json({"response": {"id": ID}}, 201)
    client.databases.create({"name": "db", "ram": 512, "type": 1, "region": "sp"})
    assert json.loads(transport.calls[0].body)["region"] == "ny"
    assert json.loads(transport.calls[1].body)["region"] == "sp"


def test_region_error_codes_are_exposed() -> None:
    assert errcodes.REGION_NOT_AVAILABLE == "REGION_NOT_AVAILABLE"
