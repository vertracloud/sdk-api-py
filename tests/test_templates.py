"""Contract of the `templates` domain: method, path, query, JSON or multipart body, the `Idempotency-Key`
header (never in the body), the deploy event stream, `confirm_detach` on the code routes and the typed errors."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from vertracloud import TemplateDeployEventStream, VertraClient, errcodes
from vertracloud.errors import ScopeDeniedError, VertraAPIError

from .fake_transport import FakeTransport, RecordedCall

ID = "11111111-1111-1111-1111-111111111111"
ID2 = "22222222-2222-2222-2222-222222222222"

JOB: dict[str, Any] = {"id": ID, "kind": "deploy", "status": "queued", "steps": [], "outputs": []}


def _client() -> tuple[VertraClient, FakeTransport]:
    transport = FakeTransport()
    return VertraClient(api_key="k", transport=transport), transport


def _query(call: RecordedCall) -> dict[str, list[str]]:
    return parse_qs(urlparse(call.url).query)


def _json_body(call: RecordedCall) -> dict[str, Any]:
    assert call.body is not None
    return json.loads(call.body)


def _has_part(call: RecordedCall, fragment: str) -> bool:
    return fragment.encode() in (call.body or b"")


# -- catalog ---------------------------------------------------------------------------------


def test_list_sends_the_filters_and_returns_the_page() -> None:
    client, transport = _client()
    page = {"data": [], "total_count": 0, "page": 2, "limit": 5, "total_pages": 0}
    transport.queue_json({"response": page})
    got = client.templates.list(
        search="n8n",
        category="automation",
        origin="private",
        tag="ai",
        fits=True,
        sort="popular",
        page=2,
        limit=5,
        workspace_id=ID,
    )
    assert got == page
    call = transport.calls[0]
    assert (call.method, call.path) == ("GET", "/v1/templates")
    assert _query(call) == {
        "search": ["n8n"], "category": ["automation"], "origin": ["private"], "tag": ["ai"], "fits": ["true"],
        "sort": ["popular"], "page": ["2"], "limit": ["5"], "workspace_id": [ID],
    }  # fmt: skip


def test_list_without_filters_has_no_query() -> None:
    client, transport = _client()
    client.templates.list()
    assert transport.calls[0].url.endswith("/v1/templates")


def test_get_by_slug_encodes_the_path_and_versions_and_categories() -> None:
    client, transport = _client()
    client.templates.get("hermes-agent")
    client.templates.versions("hermes-agent", workspace_id=ID)
    client.templates.categories()
    paths = [(c.method, c.path) for c in transport.calls]
    assert paths == [
        ("GET", "/v1/templates/hermes-agent"),
        ("GET", "/v1/templates/hermes-agent/versions"),
        ("GET", "/v1/templates/categories"),
    ]
    assert _query(transport.calls[1]) == {"workspace_id": [ID]}


def test_path_segment_is_guarded() -> None:
    client, _ = _client()
    with pytest.raises(ValueError):
        client.templates.get("..")
    with pytest.raises(ValueError):
        client.templates.share.preview("")


def test_validate_wraps_the_manifest() -> None:
    client, transport = _client()
    client.templates.validate({"id": "x"})
    client.templates.validate("id: x")
    assert _json_body(transport.calls[0]) == {"manifest": {"id": "x"}}
    assert _json_body(transport.calls[1]) == {"manifest": "id: x"}
    assert transport.calls[0].path == "/v1/templates/validate"


# -- deploy ----------------------------------------------------------------------------------


def test_deploy_sends_the_key_as_a_header_and_not_in_the_body() -> None:
    client, transport = _client()
    transport.queue_json({"response": JOB}, status=202)
    body: Any = {"name": "my-n8n", "inputs": {"admin_email": "me@example.com"}, "idempotency_key": "leak"}
    job = client.templates.deploy("n8n", body, idempotency_key="deploy-1")
    assert job == JOB
    call = transport.calls[0]
    assert (call.method, call.path) == ("POST", "/v1/templates/n8n/deploy")
    assert call.headers["Idempotency-Key"] == "deploy-1"
    assert _json_body(call) == {"name": "my-n8n", "inputs": {"admin_email": "me@example.com"}}


def test_deploy_without_a_key_sends_no_header() -> None:
    client, transport = _client()
    client.templates.deploy("n8n", {"name": "x"})
    assert "Idempotency-Key" not in transport.calls[0].headers


def test_share_deploy_uses_the_token_path_and_the_header() -> None:
    client, transport = _client()
    client.templates.share.deploy("tok/en", {"name": "x"}, idempotency_key="k")
    call = transport.calls[0]
    assert call.path == "/v1/share/templates/tok%2Fen/deploy"
    assert call.headers["Idempotency-Key"] == "k"


def test_deploys_get_and_events_paths() -> None:
    client, transport = _client()
    client.templates.deploys.get(ID)
    transport.queue_stream([b"event: end\n", b"data: {}\n", b"\n"])
    stream = client.templates.deploys.events(ID)
    assert isinstance(stream, TemplateDeployEventStream)
    list(stream)
    assert [c.path for c in transport.calls] == [f"/v1/template-deploys/{ID}", f"/v1/template-deploys/{ID}/events"]
    assert transport.calls[1].stream is True


def test_event_stream_skips_heartbeats_and_stops_at_end() -> None:
    client, transport = _client()
    first = {"deploy_id": ID, "status": "running", "current_step": "apps", "steps": [], "error": None}
    last = {"deploy_id": ID, "status": "succeeded", "current_step": None, "steps": [], "error": None}
    transport.queue_stream(
        [
            b"event: heartbeat\n",
            b"data: {}\n",
            b"\n",
            b"event: progress\n",
            f"data: {json.dumps(first)}\n".encode(),
            b"\n",
            b"event: progress\n",
            f"data: {json.dumps(last)}\n".encode(),
            b"\n",
            b"event: end\n",
            b"data: {}\n",
            b"\n",
            b"event: progress\n",
            f"data: {json.dumps(first)}\n".encode(),
            b"\n",
        ]
    )
    stream = client.templates.deploys.events(ID)
    assert stream.ended is False
    assert list(stream) == [first, last]
    assert stream.ended is True


def test_event_stream_without_end_is_not_marked_ended() -> None:
    client, transport = _client()
    transport.queue_stream([b"event: progress\n", b'data: {"deploy_id": "x"}\n', b"\n"])
    stream = client.templates.deploys.events(ID)
    assert list(stream) == [{"deploy_id": "x"}]
    assert stream.ended is False


def test_event_stream_rejects_a_broken_event() -> None:
    client, transport = _client()
    transport.queue_stream([b"event: progress\n", b"data: {nope\n", b"\n"])
    with pytest.raises(ValueError):
        list(client.templates.deploys.events(ID))


# -- private templates -----------------------------------------------------------------------


def test_create_is_multipart_with_the_manifest_changelog_and_sources() -> None:
    client, transport = _client()
    manifest = {"id": "my-api", "version": "1.0.0"}
    client.templates.create(
        {"manifest": manifest, "changelog": {"pt-br": "primeira"}, "workspace_id": ID},  # type: ignore[typeddict-item]
        sources={"web": b"PK-web", "api": b"PK-api"},
    )
    call = transport.calls[0]
    assert (call.method, call.path) == ("POST", "/v1/templates")
    assert call.headers["Content-Type"].startswith("multipart/form-data; boundary=")
    assert _has_part(call, 'name="manifest"\r\n\r\n' + json.dumps(manifest))
    assert _has_part(call, 'name="changelog"\r\n\r\n{"pt-br": "primeira"}')
    assert _has_part(call, f'name="workspace_id"\r\n\r\n{ID}')
    assert _has_part(call, 'name="sources[web]"; filename="web.zip"')
    assert _has_part(call, "Content-Type: application/zip")
    assert call.body is not None and call.body.index(b"sources[api]") < call.body.index(b"sources[web]")


def test_create_accepts_the_manifest_as_text() -> None:
    client, transport = _client()
    client.templates.create({"manifest": '{"id": "x"}'})
    assert _has_part(transport.calls[0], 'name="manifest"\r\n\r\n{"id": "x"}')


def test_new_version_posts_to_the_template() -> None:
    client, transport = _client()
    client.templates.new_version(ID, {"manifest": {"id": "x"}}, sources={"web": b"zip"}, workspace_id=ID2)
    call = transport.calls[0]
    assert (call.method, call.path) == ("POST", f"/v1/templates/{ID}/versions")
    assert _query(call) == {"workspace_id": [ID2]}
    assert not _has_part(call, 'name="workspace_id"')


def test_from_app_and_from_stack_and_drafts() -> None:
    client, transport = _client()
    client.templates.app_draft(ID)
    client.templates.stack_draft(ID)
    client.templates.from_app(
        ID,
        {
            "id": "x", "name": {"pt-br": "x"}, "description": {"pt-br": "x"}, "category": "other",
            "member": {"resource_id": ID, "service_id": "web", "env": [{"key": "A", "mode": "hidden"}]},
        },
    )  # fmt: skip
    client.templates.from_stack(
        ID,
        {"id": "x", "name": {"pt-br": "x"}, "description": {"pt-br": "x"}, "category": "other", "members": []},
        workspace_id=ID2,
    )
    paths = [(c.method, c.path) for c in transport.calls]
    assert paths == [
        ("GET", f"/v1/templates/from-app/{ID}/draft"),
        ("GET", f"/v1/templates/from-stack/{ID}/draft"),
        ("POST", f"/v1/templates/from-app/{ID}"),
        ("POST", f"/v1/templates/from-stack/{ID}"),
    ]
    assert _json_body(transport.calls[2])["member"]["env"] == [{"key": "A", "mode": "hidden"}]
    assert _query(transport.calls[3]) == {"workspace_id": [ID2]}


def test_update_delete_and_github_routes() -> None:
    client, transport = _client()
    client.templates.update(ID, {"tags": ["a"]})
    client.templates.delete(ID)
    client.templates.link_github(ID, {"repository": "acme/site", "branch": "main"})
    client.templates.unlink_github(ID)
    client.templates.report_app(ID, {"reason": "scam", "details": "x"})
    assert [(c.method, c.path) for c in transport.calls] == [
        ("PATCH", f"/v1/templates/{ID}"),
        ("DELETE", f"/v1/templates/{ID}"),
        ("PUT", f"/v1/templates/{ID}/github"),
        ("DELETE", f"/v1/templates/{ID}/github"),
        ("POST", f"/v1/apps/{ID}/template/report"),
    ]
    assert _json_body(transport.calls[2]) == {"repository": "acme/site", "branch": "main"}
    assert client.templates.delete(ID) is None


# -- share links, share, updates -------------------------------------------------------------


def test_share_links_routes() -> None:
    client, transport = _client()
    transport.queue_json({"response": {"id": ID2, "token": "t0k"}}, status=201)
    created = client.templates.share_links.create(ID, {"mode": "full_copy", "max_uses": 3, "expires_in_days": 7})
    client.templates.share_links.list(ID)
    client.templates.share_links.revoke(ID, ID2)
    assert created["token"] == "t0k"
    assert [(c.method, c.path) for c in transport.calls] == [
        ("POST", f"/v1/templates/{ID}/share-links"),
        ("GET", f"/v1/templates/{ID}/share-links"),
        ("DELETE", f"/v1/templates/{ID}/share-links/{ID2}"),
    ]
    assert _json_body(transport.calls[0]) == {"mode": "full_copy", "max_uses": 3, "expires_in_days": 7}


def test_share_routes() -> None:
    client, transport = _client()
    client.templates.share.preview("tok")
    client.templates.share.copy("tok", {"workspace_id": ID})
    client.templates.share.report("tok", {"reason": "malware"})
    assert [(c.method, c.path) for c in transport.calls] == [
        ("GET", "/v1/share/templates/tok"),
        ("POST", "/v1/share/templates/tok/copy"),
        ("POST", "/v1/share/templates/tok/report"),
    ]
    assert _json_body(transport.calls[1]) == {"workspace_id": ID}


def test_updates_routes() -> None:
    client, transport = _client()
    client.templates.updates.app_info(ID)
    client.templates.updates.app_update(ID, {"inputs": {"a": 1}, "ram": {"web": 512}})
    client.templates.updates.app_detach(ID)
    client.templates.updates.stack_info(ID, workspace_id=ID2)
    client.templates.updates.stack_update(ID)
    client.templates.updates.stack_detach(ID)
    assert [(c.method, c.path) for c in transport.calls] == [
        ("GET", f"/v1/apps/{ID}/template/update"),
        ("POST", f"/v1/apps/{ID}/template/update"),
        ("POST", f"/v1/apps/{ID}/template/detach"),
        ("GET", f"/v1/stacks/{ID}/template/update"),
        ("POST", f"/v1/stacks/{ID}/template/update"),
        ("POST", f"/v1/stacks/{ID}/template/detach"),
    ]
    assert _json_body(transport.calls[1]) == {"inputs": {"a": 1}, "ram": {"web": 512}}
    assert _json_body(transport.calls[4]) == {}
    assert transport.calls[2].body is None


# -- confirm_detach on the code routes -------------------------------------------------------


def test_confirm_detach_goes_only_when_true() -> None:
    client, transport = _client()
    apps = client.apps
    apps.files.write(ID, path="/a", content="x")
    apps.files.write(ID, path="/a", content="x", confirm_detach=True)
    apps.files.move(ID, {"path": "/a", "to": "/b", "confirm_detach": True})
    apps.files.delete(ID, path="/a", confirm_detach=True)
    apps.files.delete(ID, path="/a")
    apps.files.upload(ID, file=b"d", filename="a.py", confirm_detach=True)
    apps.files.upload(ID, file=b"d", filename="a.py")
    apps.deploys.webhook.create(
        ID, {"owner": "o", "repo_name": "r", "repo_id": "1", "account_id": "1", "confirm_detach": True}
    )
    calls = transport.calls
    assert "confirm_detach" not in _json_body(calls[0])
    assert _json_body(calls[1])["confirm_detach"] is True
    assert _json_body(calls[2])["confirm_detach"] is True
    assert _json_body(calls[3])["confirm_detach"] is True
    assert "confirm_detach" not in _json_body(calls[4])
    assert _query(calls[5]) == {"confirm_detach": ["true"]}
    assert "confirm_detach" not in calls[6].url
    assert _json_body(calls[7])["confirm_detach"] is True


# -- errors ----------------------------------------------------------------------------------


def test_manifest_invalid_exposes_the_issues() -> None:
    client, transport = _client()
    issues = [{"path": "services.web", "code": "required", "message": "x"}, "junk"]
    transport.queue_error(400, errcodes.TEMPLATE_MANIFEST_INVALID, details={"issues": issues})
    with pytest.raises(VertraAPIError) as info:
        client.templates.create({"manifest": {}})
    assert info.value.manifest_issues == [issues[0]]
    assert info.value.secret_files == []
    assert info.value.detach_action is None
    assert info.value.update_blocked is None


def test_secret_in_source_exposes_the_files() -> None:
    client, transport = _client()
    transport.queue_error(400, errcodes.TEMPLATE_SECRET_IN_SOURCE, details={"files": [".env", 3]})
    with pytest.raises(VertraAPIError) as info:
        client.templates.create({"manifest": {}})
    assert info.value.secret_files == [".env"]


def test_detach_confirmation_and_update_blocked_details() -> None:
    client, transport = _client()
    transport.queue_error(409, errcodes.TEMPLATE_DETACH_CONFIRMATION_REQUIRED, details={"action": "files.write"})
    with pytest.raises(VertraAPIError) as info:
        client.apps.files.write(ID, path="/a", content="x")
    assert info.value.detach_action == "files.write"
    transport.queue_error(409, errcodes.TEMPLATE_UPDATE_BLOCKED, details={"reason": "ram", "details": {}})
    with pytest.raises(VertraAPIError) as blocked:
        client.templates.updates.app_update(ID)
    assert blocked.value.update_blocked == {"reason": "ram", "details": {}}
    assert blocked.value.detach_action is None


def test_helpers_are_tolerant_of_odd_details() -> None:
    client, transport = _client()
    transport.queue_error(400, errcodes.TEMPLATE_MANIFEST_INVALID, details=["nope"])
    with pytest.raises(VertraAPIError) as info:
        client.templates.validate({})
    assert info.value.manifest_issues == []
    transport.queue_error(400, errcodes.TEMPLATE_MANIFEST_INVALID)
    with pytest.raises(VertraAPIError) as bare:
        client.templates.validate({})
    assert bare.value.manifest_issues == []


def test_new_codes_are_typed_by_status() -> None:
    client, transport = _client()
    transport.queue_error(403, errcodes.TEMPLATE_CLOSED)
    with pytest.raises(ScopeDeniedError) as info:
        client.apps.files.read(ID, path="/a")
    assert info.value.code == "TEMPLATE_CLOSED"


def test_error_code_constants_match_their_names() -> None:
    names = [n for n in dir(errcodes) if n.isupper()]
    assert len(names) >= 40
    assert all(getattr(errcodes, n) == n for n in names)
