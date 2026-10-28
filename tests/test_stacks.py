"""Contract of the `stacks` domain, the `workspaces.templates/stacks` links and the fields the release added to
apps, databases, images, snapshots and folders."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from vertracloud import VertraClient, errcodes
from vertracloud.errors import NotFoundError, VertraAPIError

from .fake_transport import FakeTransport, RecordedCall

ID = "11111111-1111-1111-1111-111111111111"
ID2 = "22222222-2222-2222-2222-222222222222"
CHANGE: dict[str, Any] = {"id": ID, "name": "shop", "restart_required": True, "apps_to_restart": [ID2]}


def _client() -> tuple[VertraClient, FakeTransport]:
    transport = FakeTransport()
    return VertraClient(api_key="k", transport=transport), transport


def _query(call: RecordedCall) -> dict[str, list[str]]:
    return parse_qs(urlparse(call.url).query)


def _json_body(call: RecordedCall) -> dict[str, Any]:
    assert call.body is not None
    return json.loads(call.body)


def test_list_get_and_workspace_scope() -> None:
    client, transport = _client()
    client.stacks.list(workspace_id=ID)
    client.stacks.get(ID, workspace_id=ID2)
    assert [(c.method, c.path) for c in transport.calls] == [("GET", "/v1/stacks"), ("GET", f"/v1/stacks/{ID}")]
    assert _query(transport.calls[0]) == {"workspace_id": [ID]}
    assert _query(transport.calls[1]) == {"workspace_id": [ID2]}


def test_create_returns_the_restart_notice() -> None:
    client, transport = _client()
    transport.queue_json({"response": CHANGE}, status=201)
    body: Any = {
        "name": "shop",
        "members": [{"resource_type": "application", "resource_id": ID}],
        "bindings": [{"app_id": ID, "database_id": ID2, "env_map": {"DATABASE_URL": "url"}}],
    }
    change = client.stacks.create(body)
    assert change["restart_required"] is True and change["apps_to_restart"] == [ID2]
    call = transport.calls[0]
    assert (call.method, call.path) == ("POST", "/v1/stacks")
    assert _json_body(call) == body


def test_transform_update_delete() -> None:
    client, transport = _client()
    client.stacks.transform({"folder_id": ID, "inject_variables": False, "name": "x"})
    client.stacks.update(ID, {"description": None})
    client.stacks.delete(ID, {"mode": "delete_all", "confirm_name": "shop", "blob": "keep"})
    assert [(c.method, c.path) for c in transport.calls] == [
        ("POST", "/v1/stacks/transform"),
        ("PATCH", f"/v1/stacks/{ID}"),
        ("DELETE", f"/v1/stacks/{ID}"),
    ]
    assert _json_body(transport.calls[1]) == {"description": None}
    assert _json_body(transport.calls[2]) == {"mode": "delete_all", "confirm_name": "shop", "blob": "keep"}


def test_connection_network_mode_and_additions() -> None:
    client, transport = _client()
    client.stacks.connection(ID, app_id=ID2, language="python")
    client.stacks.set_network_mode(ID, "private")
    client.stacks.add_database(ID, {"type": 1, "name": "db", "ram": 512, "bindings": [{"app_id": ID2}]})
    client.stacks.add_database_to_app(ID2, {"type": 1, "name": "db", "ram": 512, "stack_name": "s"})
    client.stacks.add_blob(ID, {"prefix": "stacks/shop/", "visibility": "private"})
    client.stacks.add_blob(ID)
    assert [(c.method, c.path) for c in transport.calls] == [
        ("GET", f"/v1/stacks/{ID}/connection"),
        ("POST", f"/v1/stacks/{ID}/network-mode"),
        ("POST", f"/v1/stacks/{ID}/databases"),
        ("POST", f"/v1/apps/{ID2}/stack/databases"),
        ("POST", f"/v1/stacks/{ID}/blob"),
        ("POST", f"/v1/stacks/{ID}/blob"),
    ]
    assert _query(transport.calls[0]) == {"app_id": [ID2], "language": ["python"]}
    assert _json_body(transport.calls[1]) == {"network_mode": "private"}
    assert _json_body(transport.calls[5]) == {}


def test_members_add_and_remove_with_query() -> None:
    client, transport = _client()
    client.stacks.members.add(ID, {"resource_type": "database", "resource_id": ID2})
    client.stacks.members.remove(ID, "blob", "stacks/x", bindings="remove_variables", blob="delete")
    add, remove = transport.calls
    assert (add.method, add.path) == ("POST", f"/v1/stacks/{ID}/members")
    assert (remove.method, remove.path) == ("DELETE", f"/v1/stacks/{ID}/members/blob/stacks%2Fx")
    assert _query(remove) == {"bindings": ["remove_variables"], "blob": ["delete"]}


def test_bindings_routes() -> None:
    client, transport = _client()
    client.stacks.bindings.list(ID)
    client.stacks.bindings.create(ID, {"app_id": ID, "blob_id": ID2})
    client.stacks.bindings.update(ID, ID2, {"DATABASE_URL": "prisma_url"})
    client.stacks.bindings.delete(ID, ID2, variables="keep_connection")
    assert [(c.method, c.path) for c in transport.calls] == [
        ("GET", f"/v1/stacks/{ID}/bindings"),
        ("POST", f"/v1/stacks/{ID}/bindings"),
        ("PATCH", f"/v1/stacks/{ID}/bindings/{ID2}"),
        ("DELETE", f"/v1/stacks/{ID}/bindings/{ID2}"),
    ]
    assert _json_body(transport.calls[2]) == {"env_map": {"DATABASE_URL": "prisma_url"}}
    assert _query(transport.calls[3]) == {"variables": ["keep_connection"]}


def test_snapshots_routes() -> None:
    client, transport = _client()
    client.stacks.snapshots.list(ID)
    client.stacks.snapshots.create(ID)
    client.stacks.snapshots.restore(ID, ID2)
    client.stacks.snapshots.restore(ID, ID2, restore_image_version=True)
    assert [(c.method, c.path) for c in transport.calls] == [
        ("GET", f"/v1/stacks/{ID}/snapshots"),
        ("POST", f"/v1/stacks/{ID}/snapshots"),
        ("POST", f"/v1/stacks/{ID}/snapshots/{ID2}/restore"),
        ("POST", f"/v1/stacks/{ID}/snapshots/{ID2}/restore"),
    ]
    assert transport.calls[2].body is None
    assert _json_body(transport.calls[3]) == {"restore_image_version": True}


def test_path_segments_are_guarded() -> None:
    client, _ = _client()
    with pytest.raises(ValueError):
        client.stacks.get("..")
    with pytest.raises(ValueError):
        client.stacks.bindings.delete(ID, "%2e%2e")


def test_stack_errors_keep_their_codes() -> None:
    client, transport = _client()
    transport.queue_error(404, errcodes.STACK_NOT_FOUND)
    with pytest.raises(NotFoundError) as info:
        client.stacks.get(ID)
    assert info.value.code == errcodes.STACK_NOT_FOUND
    transport.queue_error(409, errcodes.STACK_NAME_MISMATCH)
    with pytest.raises(VertraAPIError) as mismatch:
        client.stacks.delete(ID, {"mode": "dissolve", "confirm_name": "no"})
    assert mismatch.value.code == "STACK_NAME_MISMATCH"


# -- workspaces: move templates and stacks ---------------------------------------------------


def test_workspace_links_for_templates_and_stacks() -> None:
    client, transport = _client()
    client.workspaces.templates.add(ID, ID2)
    client.workspaces.templates.remove(ID, ID2)
    client.workspaces.stacks.add(ID, ID2)
    client.workspaces.stacks.remove(ID, ID2)
    assert [(c.method, c.path) for c in transport.calls] == [
        ("POST", f"/v1/workspaces/{ID}/templates/{ID2}"),
        ("DELETE", f"/v1/workspaces/{ID}/templates/{ID2}"),
        ("POST", f"/v1/workspaces/{ID}/stacks/{ID2}"),
        ("DELETE", f"/v1/workspaces/{ID}/stacks/{ID2}"),
    ]


# -- fields added to existing resources ------------------------------------------------------


def test_certificate_and_password_reset_return_the_restart_notice() -> None:
    client, transport = _client()
    cert = {"crt": "c", "key": "k", "pem": "p", "restart_required": True, "apps_to_restart": [ID]}
    transport.queue_json({"response": cert})
    got = client.databases.credentials.certificate.reset(ID)
    assert got["apps_to_restart"] == [ID]
    transport.queue_json({"response": {"password": "x", "restart_required": False, "apps_to_restart": []}})
    assert client.databases.credentials.password.reset(ID)["restart_required"] is False


def test_folder_bodies_carry_notes_and_flow_layout() -> None:
    client, transport = _client()
    client.account.folders.update(ID, {"notes": None, "flow_layout": {"x": 1.5, "y": 2, "collapsed": True}})
    client.workspaces.folders.create(ID, {"name": "f", "notes": "hi"})
    assert _json_body(transport.calls[0]) == {"notes": None, "flow_layout": {"x": 1.5, "y": 2, "collapsed": True}}
    assert _json_body(transport.calls[1]) == {"name": "f", "notes": "hi"}


def test_image_template_only_error_is_a_plain_api_error() -> None:
    client, transport = _client()
    transport.queue_error(403, errcodes.IMAGE_TEMPLATE_ONLY)
    with pytest.raises(VertraAPIError) as info:
        client.images.update(ID, {"name": "x"})
    assert info.value.code == "IMAGE_TEMPLATE_ONLY"
