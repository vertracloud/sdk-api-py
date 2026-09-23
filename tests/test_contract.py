"""Real per-route contract: method, path, required query, and exact body (required fields,
snake_case, multipart part names). The matrix in `test_routes_matrix.py` only proves
method+path; this file proves what that check lets through — a wrong query/body still hits
400 on the real API even with the right path (see `snapshots.*` and `deploys.webhook.create`)."""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from vertracloud import VertraClient

from .fake_transport import FakeTransport

ID = "11111111-1111-1111-1111-111111111111"
ID2 = "22222222-2222-2222-2222-222222222222"


def _client() -> tuple[VertraClient, FakeTransport]:
    transport = FakeTransport()
    return VertraClient(api_key="k", transport=transport), transport


def _call(transport: FakeTransport, index: int = 0):
    return transport.calls[index]


def _query(call) -> dict[str, list[str]]:
    return parse_qs(urlparse(call.url).query)


def _body(call) -> dict:
    assert call.body is not None
    return json.loads(call.body)


# -- snapshots: `scope` is required on all 5 routes ------------------------------------


def test_snapshots_list_all_sends_required_scope() -> None:
    client, transport = _client()
    client.snapshots.list_all("databases")
    call = _call(transport)
    assert call.method == "GET"
    assert call.path == "/v1/users/snapshots"
    assert _query(call)["scope"] == ["databases"]


def test_snapshots_list_sends_required_scope() -> None:
    client, transport = _client()
    client.snapshots.list(ID, "applications")
    call = _call(transport)
    assert call.method == "GET"
    assert call.path == f"/v1/users/{ID}/snapshots"
    assert _query(call)["scope"] == ["applications"]


def test_snapshots_download_sends_required_scope() -> None:
    client, transport = _client()
    transport.queue_binary(b"zip")
    client.snapshots.download(ID, ID2, "databases")
    call = _call(transport)
    assert call.method == "GET"
    assert call.path == f"/v1/users/{ID}/snapshots/{ID2}/download"
    assert _query(call)["scope"] == ["databases"]


def test_snapshots_create_sends_required_scope() -> None:
    client, transport = _client()
    client.snapshots.create(ID, "applications")
    call = _call(transport)
    assert call.method == "POST"
    assert call.path == f"/v1/users/{ID}/snapshots"
    assert _query(call)["scope"] == ["applications"]


def test_snapshots_restore_sends_required_scope() -> None:
    client, transport = _client()
    client.snapshots.restore(ID, ID2, "databases")
    call = _call(transport)
    assert call.method == "POST"
    assert call.path == f"/v1/users/{ID}/snapshots/{ID2}/restore"
    assert _query(call)["scope"] == ["databases"]


def test_snapshots_scope_is_a_positional_required_argument() -> None:
    client, _ = _client()
    with pytest.raises(TypeError):
        client.snapshots.list(ID)  # type: ignore[call-arg]


# -- apps.deploys.webhook.create: body with all 4 required fields ----------------------


def test_webhook_create_sends_exact_required_body() -> None:
    client, transport = _client()
    body = {"owner": "acme", "repo_name": "site", "repo_id": "123", "account_id": "456"}
    client.apps.deploys.webhook.create(ID, body)
    call = _call(transport)
    assert call.method == "POST"
    assert call.path == f"/v1/apps/{ID}/deploys/webhook"
    assert _body(call) == body


def test_webhook_create_requires_body_argument() -> None:
    client, _ = _client()
    with pytest.raises(TypeError):
        client.apps.deploys.webhook.create(ID)  # type: ignore[call-arg]


# -- databases.create/update: real validated fields, no engine/plan ---------------------


def test_databases_create_sends_required_ram_and_type() -> None:
    client, transport = _client()
    body = {"name": "meu-db", "ram": 512, "type": 1}
    client.databases.create(body)
    call = _call(transport)
    assert call.method == "POST"
    assert call.path == "/v1/databases"
    sent = _body(call)
    assert sent == body
    assert "engine" not in sent
    assert "plan" not in sent


def test_databases_update_accepts_name_description_ram_only() -> None:
    client, transport = _client()
    body = {"name": "novo-nome", "description": None, "ram": 1024}
    client.databases.update(ID, body)
    call = _call(transport)
    assert call.method == "PUT"
    assert call.path == f"/v1/databases/{ID}"
    assert _body(call) == body


# -- databases.start/stop: {status: str}, not bool or None ------------------------------


def test_databases_start_returns_status_shape() -> None:
    client, transport = _client()
    transport.queue_json({"response": {"status": "success"}})
    result = client.databases.start(ID)
    assert result == {"status": "success"}


def test_databases_stop_returns_status_shape() -> None:
    client, transport = _client()
    transport.queue_json({"response": {"status": "success"}})
    result = client.databases.stop(ID)
    assert result == {"status": "success"}


# -- apps.update_config: returns a string, not the whole app ----------------------------


def test_apps_update_config_returns_plain_string() -> None:
    client, transport = _client()
    transport.queue_json({"response": "success"})
    result = client.apps.update_config(ID, {"name": "novo-nome"})
    assert result == "success"
    call = _call(transport)
    assert call.method == "PATCH"
    assert call.path == f"/v1/apps/{ID}/config"


# -- apps.files.write: response is void -----------------------------------------------------


def test_apps_files_write_returns_none() -> None:
    client, transport = _client()
    transport.queue_json({"response": None})
    result = client.apps.files.write(ID, path="/a.py", content="x")
    assert result is None
    call = _call(transport)
    assert call.method == "PUT"
    assert call.path == f"/v1/apps/{ID}/files"


# -- multipart: exact part names ------------------------------------------------------------


def test_apps_files_upload_multipart_field_name_is_file() -> None:
    client, transport = _client()
    client.apps.files.upload(ID, file=b"conteudo", filename="a.py")
    call = _call(transport)
    assert call.method == "POST"
    assert call.path == f"/v1/apps/{ID}/files/upload"
    assert b'name="file"' in call.body
    assert b'filename="a.py"' in call.body


def test_apps_create_multipart_envs_serialized_as_json_string() -> None:
    client, transport = _client()
    client.apps.create({"name": "x", "envs": [{"key": "K", "value": "V"}]}, file=b"zip")
    call = _call(transport)
    assert call.method == "POST"
    assert call.path == "/v1/apps"
    assert b'name="file"' in call.body
    assert b'name="envs"' in call.body
    assert json.dumps([{"key": "K", "value": "V"}]).encode() in call.body


# -- snapshots.create/restore: empty body, only the `scope` query ---------------------


def test_snapshots_create_sends_empty_body() -> None:
    client, transport = _client()
    client.snapshots.create(ID, "applications")
    call = _call(transport)
    assert _body(call) == {}


def test_snapshots_restore_sends_empty_body() -> None:
    client, transport = _client()
    client.snapshots.restore(ID, ID2, "databases")
    call = _call(transport)
    assert _body(call) == {}


# -- workspaces.members.update: role_id/expires_at --------------------------------------


def test_workspaces_members_update_sends_role_id_and_expires_at() -> None:
    client, transport = _client()
    body = {"role_id": "role-1", "expires_at": None}
    client.workspaces.members.update(ID, ID2, body)
    call = _call(transport)
    assert call.method == "PUT"
    assert call.path == f"/v1/workspaces/{ID}/members/{ID2}"
    assert _body(call) == body


# -- billing.orders.create: snake_case body ----------------------------------------------


def test_billing_orders_create_sends_snake_case_body() -> None:
    client, transport = _client()
    body = {"plan": "pro", "months": 1, "type": "purchase"}
    client.billing.orders.create(body)
    call = _call(transport)
    assert call.method == "POST"
    assert call.path == "/v1/orders"
    assert _body(call) == body


# -- folders.add_resource / favorites.add: optional `position` in the body -------------


def test_account_folders_add_resource_sends_position() -> None:
    client, transport = _client()
    client.account.folders.add_resource(ID, "application", ID2, position=2)
    call = _call(transport)
    assert call.method == "PUT"
    assert _body(call) == {"position": 2}


def test_account_favorites_add_sends_position() -> None:
    client, transport = _client()
    client.account.favorites.add("application", ID2, position=2)
    call = _call(transport)
    assert call.method == "PUT"
    assert _body(call) == {"position": 2}


def test_workspace_folders_add_resource_sends_position() -> None:
    client, transport = _client()
    client.workspaces.folders.add_resource(ID, ID2, "application", ID2, position=2)
    call = _call(transport)
    assert call.method == "PUT"
    assert _body(call) == {"position": 2}


def test_workspace_favorites_add_sends_position() -> None:
    client, transport = _client()
    client.workspaces.favorites.add(ID, "application", ID2, position=2)
    call = _call(transport)
    assert call.method == "PUT"
    assert _body(call) == {"position": 2}


# -- apps.envs.set: accepts a single object or a list ------------------------------------


def test_apps_envs_set_accepts_single_object() -> None:
    client, transport = _client()
    client.apps.envs.set(ID, {"key": "K", "value": "V", "note": "n"})
    call = _call(transport)
    assert call.method == "POST"
    assert call.path == f"/v1/apps/{ID}/envs"
    assert _body(call) == {"key": "K", "value": "V", "note": "n"}


def test_apps_envs_set_accepts_list() -> None:
    client, transport = _client()
    body = [{"key": "K1", "value": "V1"}, {"key": "K2", "value": "V2"}]
    client.apps.envs.set(ID, body)
    call = _call(transport)
    assert _body(call) == body


def test_apps_create_multipart_booleans_serialized_as_true_false_strings() -> None:
    client, transport = _client()
    client.apps.create({"name": "x", "autorestart": True}, file=b"zip")
    call = _call(transport)
    body_text = call.body.decode("utf-8")
    assert 'name="autorestart"' in body_text
    assert "\r\n\r\ntrue\r\n" in body_text
