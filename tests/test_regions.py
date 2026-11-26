"""The region/node fields on the create calls, and the region error codes."""

from __future__ import annotations

import json

from vertracloud import VertraClient, errcodes

from .fake_transport import FakeTransport

ID = "11111111-1111-1111-1111-111111111111"


def _client(transport: FakeTransport) -> VertraClient:
    return VertraClient(api_key="secret-key", transport=transport)


def test_apps_create_sends_region_and_node_as_text_parts() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": ID}}, 201)
    _client(transport).apps.create({"name": "x", "region": "sp", "node": "sp1"}, file=b"zip")
    body = transport.calls[0].body
    assert b'name="region"\r\n\r\nsp\r\n' in body
    assert b'name="node"\r\n\r\nsp1\r\n' in body


def test_apps_create_omits_region_and_node_when_not_given() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": ID}}, 201)
    _client(transport).apps.create({"name": "x"}, file=b"zip")
    body = transport.calls[0].body
    assert b'name="region"' not in body
    assert b'name="node"' not in body


def test_apps_create_from_image_and_databases_create_send_region_and_node_in_json() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": ID}}, 202)
    client = _client(transport)
    client.apps.create_from_image(
        {"image_id": ID, "name": "x", "memory": 512, "web": False, "region": "ny", "node": "ny2"}
    )
    transport.queue_json({"response": {"id": ID}}, 201)
    client.databases.create({"name": "db", "ram": 512, "type": 1, "region": "sp", "node": "sp1"})
    assert json.loads(transport.calls[0].body)["region"] == "ny"
    assert json.loads(transport.calls[0].body)["node"] == "ny2"
    assert json.loads(transport.calls[1].body)["region"] == "sp"
    assert json.loads(transport.calls[1].body)["node"] == "sp1"


def test_region_error_codes_are_exposed() -> None:
    assert errcodes.REGION_NOT_AVAILABLE == "REGION_NOT_AVAILABLE"
    assert errcodes.NODE_NOT_ALLOWED == "NODE_NOT_ALLOWED"
    assert errcodes.NODE_NOT_IN_REGION == "NODE_NOT_IN_REGION"
