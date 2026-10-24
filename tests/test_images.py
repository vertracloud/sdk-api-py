"""Contract of the `images` domain (custom Docker images) and `apps.create_from_image`: method,
path, query, JSON or multipart body, the build log as an SSE line iterator, and typed errors."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from vertracloud import VertraClient
from vertracloud.errors import NotFoundError, ValidationError

from .fake_transport import FakeTransport, RecordedCall

ID = "11111111-1111-1111-1111-111111111111"
ID2 = "22222222-2222-2222-2222-222222222222"
ZIP = b"PK\x03\x04zip-bytes"

IMAGE: dict[str, Any] = {
    "id": ID,
    "name": "meu-projeto",
    "description": None,
    "owner": "account",
    "status": "building",
    "error": None,
    "digest": None,
    "uncompressed_bytes": None,
    "layer_count": None,
    "suggested_port": None,
    "apps": [],
    "github": None,
    "current_version_id": None,
    "created_at": "2026-10-23T12:00:00.000Z",
    "updated_at": "2026-10-23T12:00:00.000Z",
}


def _client() -> tuple[VertraClient, FakeTransport]:
    transport = FakeTransport()
    return VertraClient(api_key="k", transport=transport), transport


def _query(call: RecordedCall) -> dict[str, list[str]]:
    return parse_qs(urlparse(call.url).query)


def _json_body(call: RecordedCall) -> dict[str, Any]:
    assert call.body is not None
    return json.loads(call.body)


def _has_text_part(call: RecordedCall, name: str, value: str) -> bool:
    return f'name="{name}"\r\n\r\n{value}'.encode() in (call.body or b"")


def _has_file_part(call: RecordedCall, name: str, filename: str) -> bool:
    return f'name="{name}"; filename="{filename}"'.encode() in (call.body or b"")


def _has_part_named(call: RecordedCall, name: str) -> bool:
    return f'name="{name}"'.encode() in (call.body or b"")


# -- reads: GET paths -----------------------------------------------------------------------


def test_list_is_get_images_and_returns_the_array() -> None:
    client, transport = _client()
    transport.queue_json({"response": [IMAGE]})
    assert client.images.list() == [IMAGE]
    call = transport.calls[0]
    assert call.method == "GET"
    assert call.path == "/v1/images"


def test_get_uses_the_image_id_path() -> None:
    client, transport = _client()
    transport.queue_json({"response": IMAGE})
    assert client.images.get(ID) == IMAGE
    call = transport.calls[0]
    assert call.method == "GET"
    assert call.path == f"/v1/images/{ID}"


def test_get_returns_suggested_port_as_int_or_none() -> None:
    client, transport = _client()
    transport.queue_json({"response": {**IMAGE, "suggested_port": 3000}})
    assert client.images.get(ID)["suggested_port"] == 3000
    transport.queue_json({"response": IMAGE})
    assert client.images.get(ID)["suggested_port"] is None


def test_versions_is_get_on_versions_path() -> None:
    client, transport = _client()
    client.images.versions(ID)
    call = transport.calls[0]
    assert call.method == "GET"
    assert call.path == f"/v1/images/{ID}/versions"


def test_context_returns_the_download_url_object() -> None:
    client, transport = _client()
    transport.queue_json({"response": {"url": "https://example.test/ctx.zip"}})
    assert client.images.context(ID) == {"url": "https://example.test/ctx.zip"}
    call = transport.calls[0]
    assert call.method == "GET"
    assert call.path == f"/v1/images/{ID}/context"


# -- create: one source, file or GitHub, multipart -------------------------------------------


def test_create_from_zip_sends_name_file_and_workspace_as_multipart() -> None:
    client, transport = _client()
    transport.queue_json({"response": IMAGE})
    result = client.images.create({"name": "meu-projeto", "workspace_id": ID2}, file=ZIP)
    assert result == IMAGE
    call = transport.calls[0]
    assert call.method == "POST"
    assert call.path == "/v1/images"
    assert call.headers["Content-Type"].startswith("multipart/form-data; boundary=")
    assert _has_file_part(call, "file", "image.zip")
    assert ZIP in (call.body or b"")
    assert _has_text_part(call, "name", "meu-projeto")
    assert _has_text_part(call, "workspace_id", ID2)
    assert not _has_part_named(call, "github_repository")
    assert not _has_part_named(call, "github_branch")


def test_create_from_github_sends_repository_and_branch_and_no_file() -> None:
    client, transport = _client()
    client.images.create({"name": "site", "github_repository": "acme/site", "github_branch": "main"})
    call = transport.calls[0]
    assert call.method == "POST"
    assert call.path == "/v1/images"
    assert _has_text_part(call, "github_repository", "acme/site")
    assert _has_text_part(call, "github_branch", "main")
    assert not _has_part_named(call, "file")


def test_create_custom_filename_is_used() -> None:
    client, transport = _client()
    client.images.create({"name": "x"}, file=b"PK", filename="projeto.zip")
    assert _has_file_part(transport.calls[0], "file", "projeto.zip")


def test_create_from_github_without_branch_sends_repository_only() -> None:
    client, transport = _client()
    client.images.create({"name": "site", "github_repository": "acme/site"})
    call = transport.calls[0]
    assert _has_text_part(call, "github_repository", "acme/site")
    assert not _has_part_named(call, "github_branch")
    assert not _has_part_named(call, "file")


@pytest.mark.parametrize(
    "body, file",
    [
        ({"name": "x"}, None),  # no source at all
        ({"name": "x", "github_repository": "acme/site", "github_branch": "main"}, ZIP),  # both sources
        ({"name": "x", "github_branch": "main"}, None),  # branch without a repository
    ],
)
def test_create_rejects_invalid_source_before_any_request(body: dict[str, Any], file: bytes | None) -> None:
    client, transport = _client()
    with pytest.raises(ValueError):
        client.images.create(body, file=file)  # type: ignore[arg-type]
    assert transport.calls == []


# -- rebuild: PUT multipart with the whole context ------------------------------------------


def test_rebuild_is_put_multipart_with_only_the_file_part() -> None:
    client, transport = _client()
    client.images.rebuild(ID, file=ZIP)
    call = transport.calls[0]
    assert call.method == "PUT"
    assert call.path == f"/v1/images/{ID}"
    assert _has_file_part(call, "file", "image.zip")
    assert not _has_part_named(call, "name")
    assert call.timeout == 120.0


# -- description on create, update (PATCH) ----------------------------------------------------


def test_create_sends_description_only_when_given() -> None:
    client, transport = _client()
    client.images.create({"name": "site", "description": "Base Node 22", "github_repository": "acme/site"})
    client.images.create({"name": "site", "github_repository": "acme/site"})
    assert _has_text_part(transport.calls[0], "description", "Base Node 22")
    assert not _has_part_named(transport.calls[1], "description")


def test_update_is_patch_json_with_only_the_given_fields() -> None:
    client, transport = _client()
    renamed = {**IMAGE, "name": "novo", "description": "Base Node 22"}
    transport.queue_json({"response": renamed})
    result = client.images.update(ID, {"name": "novo", "description": "Base Node 22"})
    assert result == renamed
    call = transport.calls[0]
    assert call.method == "PATCH"
    assert call.path == f"/v1/images/{ID}"
    assert _json_body(call) == {"name": "novo", "description": "Base Node 22"}
    client.images.update(ID, {"name": "so-nome"})
    assert _json_body(transport.calls[1]) == {"name": "so-nome"}


def test_update_sends_null_description_to_clear_it() -> None:
    client, transport = _client()
    client.images.update(ID, {"description": None})
    assert _json_body(transport.calls[0]) == {"description": None}


def test_update_name_in_use_raises_validation_error() -> None:
    client, transport = _client()
    transport.queue_error(400, "VALIDATION_ERROR", details={"path": "name"})
    with pytest.raises(ValidationError):
        client.images.update(ID, {"name": "em-uso"})


# -- delete: confirm_name in the JSON body --------------------------------------------------


def test_delete_sends_confirm_name_in_body_and_returns_deleted_apps() -> None:
    client, transport = _client()
    transport.queue_json({"response": {"deleted_apps": [ID2]}})
    result = client.images.delete(ID, confirm_name="meu-projeto")
    assert result == {"deleted_apps": [ID2]}
    call = transport.calls[0]
    assert call.method == "DELETE"
    assert call.path == f"/v1/images/{ID}"
    assert _json_body(call) == {"confirm_name": "meu-projeto"}


def test_delete_requires_confirm_name_keyword() -> None:
    client, _ = _client()
    with pytest.raises(TypeError):
        client.images.delete(ID)  # type: ignore[call-arg]


# -- logs: SSE, one line per `log` event ----------------------------------------------------


def test_logs_yields_lines_of_log_events_only() -> None:
    client, transport = _client()
    transport.queue_stream(
        [
            b"event: log\n",
            b"data: Step 1/3\n",
            b"\n",
            b"event: system\n",
            b"data: heartbeat\n",
            b"\n",
            b"event: log\n",
            b"data: done\n",
            b"\n",
        ]
    )
    lines = list(client.images.logs(ID))
    assert lines == ["Step 1/3", "done"]
    call = transport.calls[0]
    assert call.method == "GET"
    assert call.path == f"/v1/images/{ID}/logs"
    assert call.stream is True
    assert call.headers["Accept"] == "text/event-stream"
    assert "version_id" not in _query(call)


def test_logs_sends_version_id_query_for_a_specific_version() -> None:
    client, transport = _client()
    transport.queue_stream([b"event: log\n", b"data: old\n", b"\n"])
    list(client.images.logs(ID, version_id=ID2))
    assert _query(transport.calls[0])["version_id"] == [ID2]


def test_logs_close_stops_the_stream() -> None:
    client, transport = _client()
    transport.queue_stream([b"event: log\n", b"data: a\n", b"\n", b"event: log\n", b"data: b\n", b"\n"])
    stream = client.images.logs(ID)
    first = next(iter(stream))
    assert first == "a"
    stream.close()
    assert list(stream) == []


# -- link and unlink GitHub -----------------------------------------------------------------


def test_link_github_puts_repository_and_branch_json() -> None:
    client, transport = _client()
    transport.queue_json({"response": IMAGE})
    client.images.link_github(ID, {"repository": "acme/site", "branch": "main"})
    call = transport.calls[0]
    assert call.method == "PUT"
    assert call.path == f"/v1/images/{ID}/github"
    assert _json_body(call) == {"repository": "acme/site", "branch": "main"}


def test_link_github_without_branch_sends_repository_only() -> None:
    client, transport = _client()
    transport.queue_json({"response": IMAGE})
    client.images.link_github(ID, {"repository": "acme/site"})
    assert _json_body(transport.calls[0]) == {"repository": "acme/site"}


def test_unlink_github_is_delete_on_github_path() -> None:
    client, transport = _client()
    client.images.unlink_github(ID)
    call = transport.calls[0]
    assert call.method == "DELETE"
    assert call.path == f"/v1/images/{ID}/github"
    assert call.body is None


# -- check: JSON, creates nothing -----------------------------------------------------------


def test_check_posts_dockerfile_and_file_list_as_json() -> None:
    client, transport = _client()
    report = {"refusals": [], "warnings": [{"code": "workdir_app", "line": 3}], "suggested_port": 8080}
    transport.queue_json({"response": report})
    assert client.images.check({"dockerfile": "FROM alpine\nWORKDIR /app", "files": ["Dockerfile"]}) == report
    call = transport.calls[0]
    assert call.method == "POST"
    assert call.path == "/v1/images/check"
    assert call.headers["Content-Type"] == "application/json"
    assert _json_body(call) == {"dockerfile": "FROM alpine\nWORKDIR /app", "files": ["Dockerfile"]}


# -- apps.create_from_image: JSON to /v1/apps/image -----------------------------------------


def test_apps_create_from_image_posts_json_body_to_apps_image_route() -> None:
    client, transport = _client()
    body = {
        "image_id": ID,
        "name": "meu-app",
        "memory": 512,
        "web": True,
        "subdomain": "random",
        "port": 8080,
        "envs": [{"key": "K", "value": "V"}],
        "workspace_id": ID2,
    }
    client.apps.create_from_image(body)
    call = transport.calls[0]
    assert call.method == "POST"
    assert call.path == "/v1/apps/image"
    assert call.headers["Content-Type"] == "application/json"
    assert _json_body(call) == body


def test_apps_publish_sends_port_only_in_the_body() -> None:
    client, transport = _client()
    client.apps.network.publish(ID, {"subdomain": "random", "port": 8080})
    call = transport.calls[0]
    assert call.method == "POST"
    assert call.path == f"/v1/apps/{ID}/network/publish"
    assert _json_body(call) == {"subdomain": "random", "port": 8080}


# -- typed errors ---------------------------------------------------------------------------


def test_delete_with_wrong_confirm_name_raises_validation_error() -> None:
    client, transport = _client()
    transport.queue_error(400, "IMAGE_NAME_MISMATCH")
    with pytest.raises(ValidationError) as info:
        client.images.delete(ID, confirm_name="outro")
    assert info.value.code == "IMAGE_NAME_MISMATCH"


def test_get_unknown_image_raises_not_found_error() -> None:
    client, transport = _client()
    transport.queue_error(404, "IMAGE_NOT_FOUND")
    with pytest.raises(NotFoundError) as info:
        client.images.get(ID)
    assert info.value.code == "IMAGE_NOT_FOUND"


def test_dockerfile_refused_exposes_the_issues_on_the_error() -> None:
    client, transport = _client()
    transport.queue_error(
        400,
        "DOCKERFILE_REFUSED",
        details={"issues": [{"code": "run_network_host", "line": 4}, "lixo", {"code": "mount_ssh", "line": None}]},
    )
    with pytest.raises(ValidationError) as info:
        client.images.create({"name": "x"}, file=ZIP)
    assert info.value.code == "DOCKERFILE_REFUSED"
    # Entries that are not objects are dropped instead of failing the error handling.
    assert info.value.issues == [{"code": "run_network_host", "line": 4}, {"code": "mount_ssh", "line": None}]


@pytest.mark.parametrize(
    "details",
    [None, "texto", ["lista"], {"outro": 1}, {"issues": "nao-e-lista"}],
)
def test_issues_is_empty_when_details_have_no_issue_list(details: Any) -> None:
    client, transport = _client()
    transport.queue_error(400, "DOCKERFILE_REFUSED", details=details)
    with pytest.raises(ValidationError) as info:
        client.images.create({"name": "x"}, file=ZIP)
    assert info.value.issues == []


# -- workspace_id: query on every route that acts on an existing image, and on GET /v1/images --

WS = "33333333-3333-3333-3333-333333333333"

WORKSPACE_ACTS: list[tuple[str, str, str, Callable[[VertraClient, str | None], object]]] = [
    ("list", "GET", "/v1/images", lambda c, ws: c.images.list(workspace_id=ws)),
    ("get", "GET", f"/v1/images/{ID}", lambda c, ws: c.images.get(ID, workspace_id=ws)),
    ("update", "PATCH", f"/v1/images/{ID}", lambda c, ws: c.images.update(ID, {"name": "novo"}, workspace_id=ws)),
    ("rebuild", "PUT", f"/v1/images/{ID}", lambda c, ws: c.images.rebuild(ID, file=ZIP, workspace_id=ws)),
    (
        "delete",
        "DELETE",
        f"/v1/images/{ID}",
        lambda c, ws: c.images.delete(ID, confirm_name="meu-projeto", workspace_id=ws),
    ),
    ("versions", "GET", f"/v1/images/{ID}/versions", lambda c, ws: c.images.versions(ID, workspace_id=ws)),
    ("context", "GET", f"/v1/images/{ID}/context", lambda c, ws: c.images.context(ID, workspace_id=ws)),
    (
        "link_github",
        "PUT",
        f"/v1/images/{ID}/github",
        lambda c, ws: c.images.link_github(ID, {"repository": "acme/site", "branch": "main"}, workspace_id=ws),
    ),
    ("unlink_github", "DELETE", f"/v1/images/{ID}/github", lambda c, ws: c.images.unlink_github(ID, workspace_id=ws)),
]


@pytest.mark.parametrize("name, method, path, act", WORKSPACE_ACTS, ids=[a[0] for a in WORKSPACE_ACTS])
def test_workspace_id_is_sent_as_query(
    name: str, method: str, path: str, act: Callable[[VertraClient, str | None], object]
) -> None:
    client, transport = _client()
    act(client, WS)
    call = transport.calls[0]
    assert call.method == method
    assert call.path == path
    assert _query(call) == {"workspace_id": [WS]}


@pytest.mark.parametrize("name, method, path, act", WORKSPACE_ACTS, ids=[a[0] for a in WORKSPACE_ACTS])
def test_no_query_when_workspace_id_is_omitted(
    name: str, method: str, path: str, act: Callable[[VertraClient, str | None], object]
) -> None:
    client, transport = _client()
    act(client, None)
    assert "?" not in transport.calls[0].url


def test_logs_sends_workspace_id_beside_version_id() -> None:
    client, transport = _client()
    transport.queue_stream([b"event: log\n", b"data: x\n", b"\n"])
    list(client.images.logs(ID, version_id=ID2, workspace_id=WS))
    call = transport.calls[0]
    assert call.path == f"/v1/images/{ID}/logs"
    assert _query(call) == {"version_id": [ID2], "workspace_id": [WS]}


def test_logs_without_workspace_or_version_sends_no_query() -> None:
    client, transport = _client()
    transport.queue_stream([b"event: log\n", b"data: x\n", b"\n"])
    list(client.images.logs(ID))
    assert "?" not in transport.calls[0].url
