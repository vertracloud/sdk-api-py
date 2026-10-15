"""Blob Storage: route/method/query/body of each method, upload path choice, part retry, resume."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from vertracloud import VertraAPIError, VertraClient
from vertracloud.resources import blob as blob_mod

from .fake_transport import FakeTransport, RecordedCall

BASE = "https://blob.vertracloud.app/v1"
OBJ = {"id": "1", "path": "a/b.txt"}


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(blob_mod.time, "sleep", lambda _s: None)


def _setup() -> tuple[VertraClient, FakeTransport]:
    t = FakeTransport()
    return VertraClient(api_key="k", transport=t), t


def _q(call: RecordedCall) -> dict[str, list[str]]:
    return parse_qs(urlparse(call.url).query)


def _body(call: RecordedCall) -> dict:
    return json.loads(call.body or b"")


def test_default_and_custom_base_url() -> None:
    client, t = _setup()
    t.queue_json({"response": {}})
    client.blob.stats()
    assert t.calls[0].url == f"{BASE}/stats"
    assert t.calls[0].headers["Authorization"] == "Bearer k"
    c2 = VertraClient(api_key="k", transport=t, blob_base_url="http://x.test/v1/")
    c2.blob.stats()
    assert t.calls[1].url == "http://x.test/v1/stats"
    assert client.base_url == "https://api.vertracloud.app"


def test_put_small_is_multipart_on_objects() -> None:
    client, t = _setup()
    t.queue_json({"response": OBJ})
    seen: list[tuple[int, int]] = []
    out = client.blob.put(
        "a/b.txt",
        b"hello",
        visibility="public",
        overwrite=True,
        random_suffix=False,
        metadata={"owner": "joao"},
        on_progress=lambda a, b: seen.append((a, b)),
        workspace_id="w1",
    )
    assert out == OBJ
    c = t.calls[0]
    assert (c.method, c.path) == ("POST", "/v1/objects")
    assert c.headers["Content-Type"].startswith("multipart/form-data")
    q = _q(c)
    assert q["path"] == ["a/b.txt"] and q["visibility"] == ["public"]
    assert q["overwrite"] == ["true"] and q["random_suffix"] == ["false"] and q["workspace_id"] == ["w1"]
    assert json.loads(q["metadata"][0]) == {"owner": "joao"}
    assert b'name="file"' in (c.body or b"") and b"hello" in (c.body or b"")
    assert seen == [(5, 5)]
    assert len(t.calls) == 1


def test_put_and_copy_send_rename_on_conflict() -> None:
    client, t = _setup()
    t.queue_json({"response": OBJ})
    t.queue_json({"response": OBJ})
    client.blob.put("a/b.txt", b"hi", rename_on_conflict=True)
    assert _q(t.calls[0])["rename_on_conflict"] == ["true"]
    client.blob.copy("o1", "a/b.txt", rename_on_conflict=True)
    assert json.loads(t.calls[1].body or b"{}") == {"source": "o1", "path": "a/b.txt", "rename_on_conflict": True}


def test_put_from_path(tmp_path: Path) -> None:
    f = tmp_path / "x.txt"
    f.write_bytes(b"from-disk")
    client, t = _setup()
    t.queue_json({"response": OBJ})
    client.blob.put("x.txt", str(f))
    assert b"from-disk" in (t.calls[0].body or b"") and b'filename="x.txt"' in (t.calls[0].body or b"")


def test_put_large_single_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(blob_mod, "SIMPLE_UPLOAD_MAX_BYTES", 4)
    client, t = _setup()
    t.queue_json(
        {
            "response": {
                "id": "u1",
                "mode": "single",
                "size": 10,
                "url": "https://s.test/put?sig=1",
                "headers": {"Content-Type": "text/plain"},
            }
        }
    )
    t.queue_json({}, status=200)  # storage PUT
    t.queue_json({"response": OBJ})
    seen: list[tuple[int, int]] = []
    out = client.blob.put(
        "big.txt", b"0123456789", expires_at="2030-01-01T00:00:00Z", on_progress=lambda a, b: seen.append((a, b))
    )
    assert out == OBJ
    create, put, complete = t.calls
    assert (create.method, create.path) == ("POST", "/v1/uploads")
    assert _body(create) == {"path": "big.txt", "size": 10, "expires_at": "2030-01-01T00:00:00Z"}
    assert put.method == "PUT" and put.url == "https://s.test/put?sig=1" and put.body == b"0123456789"
    assert put.headers == {"Content-Type": "text/plain"}  # exactly the signed headers, no API key
    assert (complete.method, complete.path) == ("POST", "/v1/uploads/u1/complete")
    assert seen == [(10, 10)]


def _multipart_upload(uploaded: list[int] | None = None) -> dict:
    up = {"id": "u2", "mode": "multipart", "size": 10, "part_size": 4, "part_count": 3, "headers": {}}
    if uploaded is not None:
        up["uploaded_parts"] = uploaded
    return up


def _parts(*numbers: int) -> dict:
    sizes = {1: 4, 2: 4, 3: 2}
    return {
        "response": [
            {"part_number": n, "url": f"https://s.test/p{n}", "size": sizes[n], "headers": {"X-P": str(n)}}
            for n in numbers
        ]
    }


def test_put_multipart_with_part_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(blob_mod, "SIMPLE_UPLOAD_MAX_BYTES", 4)
    client, t = _setup()
    t.queue_json({"response": _multipart_upload()})
    t.queue_json(_parts(1, 2, 3))
    t.queue_json({}, status=200)  # part 1
    t.queue_error(503, "UNAVAILABLE")  # part 2 fails once
    t.queue_json({}, status=200)  # part 2 retry
    t.queue_json({}, status=200)  # part 3
    t.queue_json({"response": OBJ})
    seen: list[tuple[int, int]] = []
    client.blob.put("big.bin", b"0123456789", on_progress=lambda a, b: seen.append((a, b)))
    calls = t.calls
    assert _body(calls[1]) == {"part_numbers": [1, 2, 3]} and calls[1].path == "/v1/uploads/u2/parts"
    puts = [c for c in calls if c.method == "PUT"]
    assert [(c.url, c.body) for c in puts] == [
        ("https://s.test/p1", b"0123"),
        ("https://s.test/p2", b"4567"),
        ("https://s.test/p2", b"4567"),
        ("https://s.test/p3", b"89"),
    ]
    assert all("Authorization" not in c.headers for c in puts)
    assert calls[-1].path == "/v1/uploads/u2/complete"
    assert seen == [(4, 10), (8, 10), (10, 10)]


def test_part_client_error_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(blob_mod, "SIMPLE_UPLOAD_MAX_BYTES", 4)
    client, t = _setup()
    t.queue_json({"response": _multipart_upload()})
    t.queue_json(_parts(1, 2, 3))
    t.queue_error(403, "EXPIRED")
    with pytest.raises(VertraAPIError):
        client.blob.put("big.bin", b"0123456789")
    assert len([c for c in t.calls if c.method == "PUT"]) == 1


def test_resume_sends_only_missing_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    client, t = _setup()
    t.queue_json({"response": _multipart_upload([1, 3])})
    t.queue_json(_parts(2))
    t.queue_json({}, status=200)
    t.queue_json({"response": OBJ})
    seen: list[tuple[int, int]] = []
    client.blob.resume("u2", b"0123456789", on_progress=lambda a, b: seen.append((a, b)))
    assert (t.calls[0].method, t.calls[0].path) == ("GET", "/v1/uploads/u2")
    assert _body(t.calls[1]) == {"part_numbers": [2]}
    assert t.calls[2].body == b"4567"
    assert seen[-1] == (10, 10)
    t.queue_json({"response": _multipart_upload([1, 3])})
    with pytest.raises(ValueError):
        client.blob.resume("u2", b"short")


def test_part_urls_requested_in_batches_of_100(monkeypatch: pytest.MonkeyPatch) -> None:
    client, t = _setup()
    up = {"id": "u3", "mode": "multipart", "size": 150, "part_size": 1, "part_count": 150, "headers": {}}
    t.queue_json({"response": up})
    t.queue_json(
        {
            "response": [
                {"part_number": n, "url": f"https://s.test/{n}", "size": 1, "headers": {}} for n in range(1, 101)
            ]
        }
    )
    for _ in range(100):
        t.queue_json({})  # storage PUTs of the first batch
    t.queue_json(
        {
            "response": [
                {"part_number": n, "url": f"https://s.test/{n}", "size": 1, "headers": {}} for n in range(101, 151)
            ]
        }
    )
    client.blob.resume("u3", b"x" * 150)
    batches = [_body(c)["part_numbers"] for c in t.calls if c.path.endswith("/parts")]
    assert [len(b) for b in batches] == [100, 50]


def test_list_follows_cursor() -> None:
    client, t = _setup()
    t.queue_json({"response": {"objects": [{"id": "1"}], "folders": [], "cursor": "c1"}})
    t.queue_json({"response": {"objects": [{"id": "2"}], "folders": [], "cursor": None}})
    items = list(client.blob.list("img/", "/", "public", workspace_id="w"))
    assert [i["id"] for i in items] == ["1", "2"]
    assert (t.calls[0].method, t.calls[0].path) == ("GET", "/v1/objects")
    assert _q(t.calls[0]) == {"prefix": ["img/"], "delimiter": ["/"], "visibility": ["public"], "workspace_id": ["w"]}
    assert _q(t.calls[1])["cursor"] == ["c1"]


def test_get_update_copy_move_delete() -> None:
    client, t = _setup()
    client.blob.get("a/b")
    assert (t.calls[0].method, t.calls[0].path) == ("GET", "/v1/objects/a%2Fb")
    client.blob.update("7", metadata={"k": None}, filename=None, workspace_id="w")
    assert (t.calls[1].method, t.calls[1].path) == ("PATCH", "/v1/objects/7")
    assert _body(t.calls[1]) == {"metadata": {"k": None}, "filename": None} and _q(t.calls[1]) == {
        "workspace_id": ["w"]
    }
    client.blob.copy("7", "c.txt", overwrite=True)
    assert (t.calls[2].method, t.calls[2].path) == ("POST", "/v1/objects/copy")
    assert _body(t.calls[2]) == {"source": "7", "path": "c.txt", "overwrite": True}
    client.blob.move("7", "d.txt")
    assert _body(t.calls[3]) == {"source": "7", "path": "d.txt", "move": True}
    client.blob.delete("7")
    assert (t.calls[4].method, t.calls[4].path) == ("DELETE", "/v1/objects/7")


def test_update_many_batches() -> None:
    client, t = _setup()
    t.queue_json({"response": [{"id": "a", "ok": True}]})
    t.queue_json({"response": [{"id": "b", "ok": True}]})
    out = client.blob.update_many([str(i) for i in range(101)], visibility="private")
    assert len(out) == 2
    assert (t.calls[0].method, t.calls[0].path) == ("PATCH", "/v1/objects")
    assert len(_body(t.calls[0])["ids"]) == 100 and _body(t.calls[1])["ids"] == ["100"]
    assert _body(t.calls[0])["changes"] == {"visibility": "private"}


def test_delete_many_repeats_while_remaining() -> None:
    client, t = _setup()
    t.queue_json({"response": {"deleted": ["1", "2"], "not_found": [], "remaining": True}})
    t.queue_json({"response": {"deleted": ["3"], "not_found": ["9"], "remaining": False}})
    out = client.blob.delete_many(prefix="tmp/")
    assert out == {"deleted": ["1", "2", "3"], "not_found": ["9"], "remaining": False}
    assert [(_body(c)) for c in t.calls] == [{"prefix": "tmp/"}] * 2
    assert t.calls[0].method == "DELETE" and t.calls[0].path == "/v1/objects"
    t.queue_json({"response": {"deleted": ["1"], "not_found": [], "remaining": False}})
    client.blob.delete_many(ids=["1"])
    assert _body(t.calls[2]) == {"ids": ["1"]}
    with pytest.raises(ValueError):
        client.blob.delete_many()


def test_download_url_uses_redirect_false() -> None:
    client, t = _setup()
    client.blob.download_url("7", expires_in=600, disposition="attachment", filename="f.txt")
    c = t.calls[0]
    assert (c.method, c.path) == ("GET", "/v1/objects/7/download")
    assert _q(c) == {"expires_in": ["600"], "disposition": ["attachment"], "filename": ["f.txt"], "redirect": ["false"]}


def test_rules() -> None:
    client, t = _setup()
    client.blob.rules.get()
    assert (t.calls[0].method, t.calls[0].path) == ("GET", "/v1/rules")
    client.blob.rules.set([{"prefix": "tmp/", "max_size": 5}], "etag-1")
    c = t.calls[1]
    assert (c.method, c.path, c.headers["If-Match"]) == ("PUT", "/v1/rules", "etag-1")
    assert _body(c) == {"rules": [{"prefix": "tmp/", "max_size": 5}]}
    client.blob.rules.put("tmp/a b/", delete_after_days=30)
    assert (t.calls[2].method, urlparse(t.calls[2].url).path) == ("PUT", "/v1/rules/tmp%2Fa%20b%2F")
    assert _body(t.calls[2]) == {"delete_after_days": 30}
    client.blob.rules.delete("tmp/")
    assert (t.calls[3].method, urlparse(t.calls[3].url).path) == ("DELETE", "/v1/rules/tmp%2F")


def test_shares_domains_account() -> None:
    client, t = _setup()
    client.blob.shares.create("7", max_downloads=10, password="12345678")
    assert (t.calls[0].method, t.calls[0].path) == ("POST", "/v1/shares")
    assert _body(t.calls[0]) == {"object_id": "7", "max_downloads": 10, "password": "12345678"}
    client.blob.shares.list("7")
    assert _q(t.calls[1]) == {"object_id": ["7"]}
    client.blob.shares.revoke("s1")
    assert (t.calls[2].method, t.calls[2].path) == ("DELETE", "/v1/shares/s1")
    client.blob.domains.list()
    client.blob.domains.add("cdn.x.com", "img/", web_content=True)
    assert _body(t.calls[4]) == {"hostname": "cdn.x.com", "prefix": "img/", "web_content": True}
    client.blob.domains.update("d1", web_content=False)
    assert (t.calls[5].method, t.calls[5].path) == ("PATCH", "/v1/domains/d1")
    assert _body(t.calls[5]) == {"web_content": False}
    client.blob.domains.verify("d1")
    assert (t.calls[6].method, t.calls[6].path) == ("POST", "/v1/domains/d1/verify")
    client.blob.domains.delete("d1")
    assert (t.calls[7].method, t.calls[7].path) == ("DELETE", "/v1/domains/d1")
    client.blob.stats()
    assert t.calls[8].path == "/v1/stats"
    client.blob.create_upload_token(prefix="avatars/", max_size=100)
    assert (t.calls[9].method, t.calls[9].path) == ("POST", "/v1/upload-tokens")
    assert _body(t.calls[9]) == {"prefix": "avatars/", "max_size": 100}
    client.blob.s3_credentials(workspace_id="w")
    assert t.calls[10].path == "/v1/s3/credentials" and _q(t.calls[10]) == {"workspace_id": ["w"]}
    client.blob.uploads()
    client.blob.abort_upload("u1")
    assert (t.calls[12].method, t.calls[12].path) == ("DELETE", "/v1/uploads/u1")


def test_blob_error_code_passes_through() -> None:
    client, t = _setup()
    t.queue_error(403, "STORAGE_QUOTA_EXCEEDED")
    with pytest.raises(VertraAPIError) as exc:
        client.blob.put("a.txt", b"x")
    assert exc.value.code == "STORAGE_QUOTA_EXCEEDED" and exc.value.status == 403
