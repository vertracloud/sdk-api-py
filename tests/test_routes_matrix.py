"""Proves (a) every frozen route has a method that generates exactly that method+path,
(b) no method generates a path outside the list, (c) no forbidden path appears in the source."""

from __future__ import annotations

import re
from pathlib import Path

from vertracloud import VertraClient

from .fake_transport import FakeTransport
from .routes_matrix import FORBIDDEN_PATHS, FROZEN_ROUTES, route_to_regex

ID = "11111111-1111-1111-1111-111111111111"
ID2 = "22222222-2222-2222-2222-222222222222"


def _drive_all_calls(client: VertraClient, transport: FakeTransport) -> None:
    """Calls EVERY public method of every resource, once, with minimal valid args."""
    apps = client.apps
    apps.get(ID)
    apps.status(ID)
    apps.status_all()
    apps.runtimes()
    apps.metrics(ID)
    apps.logs(ID)
    apps.download(ID)
    transport.queue_stream([b"event: system\n", b"data: hi\n", b"\n"])
    stream = apps.realtime(ID)
    stream.close()
    apps.create({"name": "x"}, file=b"zip-bytes")
    apps.start(ID)
    apps.stop(ID)
    apps.restart(ID)
    apps.update_config(ID, {"name": "x"})
    apps.delete(ID)
    apps.deploys.list(ID)
    apps.deploys.webhook.get(ID)
    apps.deploys.webhook.create(ID, {"owner": "o", "repo_name": "r", "repo_id": "1", "account_id": "1"})
    apps.deploys.webhook.delete(ID)
    apps.releases.list(ID)
    apps.releases.log(ID, ID2)
    apps.releases.preview_rollback(ID, ID2)
    apps.releases.rollback(ID, ID2)
    apps.domains.list(ID)
    apps.domains.add(ID, {"hostname": "example.com"})
    apps.domains.update(ID, ID2, {"port": 8080})
    apps.domains.remove(ID, ID2)
    apps.domains.dns(ID, ID2)
    apps.domains.connect(ID, ID2)
    apps.network.purge_cache(ID)
    apps.network.set_subdomain(ID, {"subdomain": "abc"})
    apps.network.publish(ID)
    apps.network.unpublish(ID)
    apps.envs.list(ID)
    apps.envs.set(ID, {"key": "K", "value": "V"})
    apps.envs.delete(ID, ID2)
    apps.files.list(ID)
    apps.files.tree(ID)
    apps.files.read(ID, path="/a.py")
    apps.files.write(ID, path="/a.py", content="x")
    apps.files.move(ID, {"path": "/a.py", "to": "/b.py"})
    apps.files.delete(ID, path="/a.py")
    apps.files.upload(ID, file=b"data", filename="a.py")
    apps.create_from_image({"image_id": ID, "name": "x", "memory": 512, "web": False})

    databases = client.databases
    databases.status_all()
    databases.versions()
    databases.get(ID)
    databases.status(ID)
    databases.metrics(ID)
    databases.create({"name": "db", "ram": 512, "type": 1})
    databases.update(ID, {"name": "db2"})
    databases.start(ID)
    databases.stop(ID)
    databases.reset(ID)
    databases.delete(ID)
    databases.credentials.certificate.get(ID)
    databases.credentials.certificate.reset(ID)
    databases.credentials.password.reset(ID)

    snapshots = client.snapshots
    snapshots.list_all("applications")
    snapshots.list(ID, "applications")
    snapshots.download(ID, ID2, "applications")
    snapshots.create(ID, "applications")
    snapshots.restore(ID, ID2, "applications")

    account = client.account
    account.get()
    account.update({"name": "x"})
    account.sessions.list()
    account.folders.create({"name": "f"})
    account.folders.update(ID, {"name": "f2"})
    account.folders.delete(ID)
    account.folders.add_resource(ID, "app", ID2)
    account.folders.remove_resource(ID, "app", ID2)
    account.favorites.add("app", ID2)
    account.favorites.remove("app", ID2)

    workspaces = client.workspaces
    workspaces.list()
    workspaces.get(ID)
    workspaces.create({"name": "w"})
    workspaces.update(ID, {"name": "w2"})
    workspaces.delete(ID)
    workspaces.invites.list(ID)
    workspaces.invites.revoke(ID, ID2)
    workspaces.invites.preview("tok")
    workspaces.invites.accept("tok")
    workspaces.invites.decline("tok")
    workspaces.action_requests.list(ID, status="pending")
    workspaces.action_requests.create(ID, {"action": "app_delete", "resource_id": ID2})
    workspaces.members.list(ID)
    workspaces.members.update(ID, ID2, {"role_id": "r"})
    workspaces.members.remove(ID, ID2)
    workspaces.roles.list(ID)
    workspaces.roles.create(ID, {"name": "r"})
    workspaces.roles.update(ID, ID2, {"name": "r2"})
    workspaces.roles.delete(ID, ID2)
    workspaces.apps.add(ID, ID2)
    workspaces.apps.remove(ID, ID2)
    workspaces.databases.add(ID, ID2)
    workspaces.databases.remove(ID, ID2)
    workspaces.folders.create(ID, {"name": "f"})
    workspaces.folders.update(ID, ID2, {"name": "f2"})
    workspaces.folders.delete(ID, ID2)
    workspaces.folders.add_resource(ID, ID2, "app", ID)
    workspaces.folders.remove_resource(ID, ID2, "app", ID)
    workspaces.favorites.add(ID, "app", ID2)
    workspaces.favorites.remove(ID, "app", ID2)

    billing = client.billing
    billing.orders.list()
    billing.orders.status("order-1")
    billing.orders.create({"plan": "pro"})
    billing.orders.initiate_pix("order-1")
    billing.details()
    billing.update_details({"name": "x", "address": {"line1": "x", "city": "x", "country": "US"}})
    billing.redeem("CODE123")

    images = client.images
    images.list()
    images.create({"name": "img"}, file=b"zip-bytes")
    images.create({"name": "img", "github_repository": "acme/site", "github_branch": "main"})
    images.get(ID)
    images.update(ID, {"name": "img2"})
    images.rebuild(ID, file=b"zip-bytes")
    images.delete(ID, confirm_name="img")
    images.versions(ID)
    transport.queue_stream([b"event: log\n", b"data: step\n", b"\n"])
    build_log = images.logs(ID, version_id=ID2)
    build_log.close()
    images.context(ID)
    images.link_github(ID, {"repository": "acme/site", "branch": "main"})
    images.unlink_github(ID)
    images.check({"dockerfile": "FROM alpine", "files": ["Dockerfile"]})

    templates = client.templates
    templates.list()
    templates.get("n8n")
    templates.categories()
    templates.versions("n8n")
    templates.validate({"id": "x"})
    templates.deploy("n8n", {"name": "my-n8n"})
    templates.create({"manifest": {"id": "x"}}, sources={"web": b"zip"})
    templates.new_version(ID, {"manifest": {"id": "x"}})
    templates.from_app(
        ID,
        {
            "id": "x",
            "name": {"pt-br": "x"},
            "description": {"pt-br": "x"},
            "category": "other",
            "member": {"resource_id": ID2, "service_id": "web"},
        },
    )
    templates.from_stack(
        ID, {"id": "x", "name": {"pt-br": "x"}, "description": {"pt-br": "x"}, "category": "other", "members": []}
    )
    templates.app_draft(ID)
    templates.stack_draft(ID)
    templates.update(ID, {"tags": ["a"]})
    templates.delete(ID)
    templates.link_github(ID, {"repository": "acme/site"})
    templates.unlink_github(ID)
    templates.report_app(ID, {"reason": "other"})
    templates.deploys.get(ID)
    transport.queue_stream([b"event: end\n", b"data: {}\n", b"\n"])
    list(templates.deploys.events(ID))
    templates.share_links.create(ID, {"mode": "use"})
    templates.share_links.list(ID)
    templates.share_links.revoke(ID, ID2)
    templates.share.preview("tok")
    templates.share.deploy("tok", {"name": "x"})
    templates.share.copy("tok")
    templates.share.report("tok", {"reason": "other"})
    templates.updates.app_info(ID)
    templates.updates.app_update(ID)
    templates.updates.app_detach(ID)
    templates.updates.stack_info(ID)
    templates.updates.stack_update(ID)
    templates.updates.stack_detach(ID)

    stacks = client.stacks
    stacks.list()
    stacks.get(ID)
    stacks.create({"name": "s"})
    stacks.transform({"folder_id": ID, "inject_variables": True})
    stacks.update(ID, {"name": "s2"})
    stacks.delete(ID, {"mode": "dissolve", "confirm_name": "s"})
    stacks.connection(ID, app_id=ID2)
    stacks.set_network_mode(ID, "public")
    stacks.add_database(ID, {"type": 1, "name": "db", "ram": 512})
    stacks.add_database_to_app(ID, {"type": 1, "name": "db", "ram": 512})
    stacks.add_blob(ID)
    stacks.members.add(ID, {"resource_type": "application", "resource_id": ID2})
    stacks.members.remove(ID, "application", ID2)
    stacks.bindings.list(ID)
    stacks.bindings.create(ID, {"app_id": ID2})
    stacks.bindings.update(ID, ID2, {"DATABASE_URL": "url"})
    stacks.bindings.delete(ID, ID2)
    stacks.snapshots.list(ID)
    stacks.snapshots.create(ID)
    stacks.snapshots.restore(ID, ID2)
    workspaces.templates.add(ID, ID2)
    workspaces.templates.remove(ID, ID2)
    workspaces.stacks.add(ID, ID2)
    workspaces.stacks.remove(ID, ID2)


def test_every_frozen_route_is_generated_exactly_once() -> None:
    transport = FakeTransport()
    client = VertraClient(api_key="secret", transport=transport)
    _drive_all_calls(client, transport)

    frozen_regexes = [(m, p, re.compile(route_to_regex(p))) for m, p in FROZEN_ROUTES]
    matched_routes: set[tuple[str, str]] = set()
    unmatched_calls: list[tuple[str, str]] = []

    for call in transport.calls:
        hits = [(m, p) for m, p, rx in frozen_regexes if m == call.method and rx.match(call.path)]
        if not hits:
            unmatched_calls.append((call.method, call.path))
        else:
            matched_routes.update(hits)

    assert not unmatched_calls, f"calls outside the frozen matrix: {unmatched_calls}"
    missing = set(FROZEN_ROUTES) - matched_routes
    assert not missing, f"routes in the matrix never generated by any method: {missing}"


def test_no_forbidden_path_in_source() -> None:
    src_root = Path(__file__).resolve().parent.parent / "src" / "vertracloud"
    offenders: list[str] = []
    for py_file in src_root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_PATHS:
            if forbidden in text:
                offenders.append(f"{py_file}: {forbidden}")
    assert not offenders, f"forbidden path found in source: {offenders}"


def test_fixture_matches_api_key_catalog() -> None:
    """The fixture must exactly match the public API key catalog. Only runs in the monorepo,
    where `api-types` is a sibling of this repo."""
    import pytest

    catalog = Path(__file__).resolve().parents[2] / "api-types" / "payloads" / "v1" / "api-key.ts"
    if not catalog.exists():
        pytest.skip("api-types is not next to this repo")
    routes = set(re.findall(r'\{ method: "([A-Z]+)", path: "([^"]+)" \}', catalog.read_text(encoding="utf-8")))
    # Blob Storage lives on its own host (`client.blob`), covered by `test_blob.py`.
    routes = {r for r in routes if not r[1].startswith("/v1/blob/")}
    assert routes == set(FROZEN_ROUTES)
