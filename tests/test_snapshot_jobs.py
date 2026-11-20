"""Restore as a job, `snapshot_jobs`, `restore_job_id` on create and `apps.download` (snapshot, then its zip)."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from vertracloud import (
    NotFoundError,
    RateLimitError,
    SnapshotJobError,
    SnapshotJobFailedError,
    SnapshotJobSkippedError,
    SnapshotJobTimeoutError,
    VertraAPIError,
    VertraClient,
    errcodes,
)

from .fake_transport import FakeTransport

ID = "11111111-1111-1111-1111-111111111111"
SNAP = "22222222-2222-2222-2222-222222222222"
JOB = "33333333-3333-3333-3333-333333333333"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    slept: list[float] = []
    monkeypatch.setattr("time.sleep", slept.append)
    return slept


def make(transport: FakeTransport) -> VertraClient:
    return VertraClient(api_key="k", transport=transport)


def _query(transport: FakeTransport, index: int = -1) -> dict[str, list[str]]:
    return parse_qs(urlparse(transport.calls[index].url).query)


def _job(status: str, **extra: Any) -> dict[str, Any]:
    base = {
        "id": JOB,
        "kind": "restore",
        "resource_id": ID,
        "status": status,
        "created_at": "2026-11-16T10:00:00.000Z",
    }
    return {"response": {**base, **extra}}


# -- restore ----------------------------------------------------------------


def test_restore_returns_the_job_id_and_the_warning() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"job_id": JOB, "warning": "IMAGE_VERSION_NOT_FOUND"}}, status=202)
    result = make(transport).snapshots.restore(ID, SNAP, "applications")
    assert result == {"job_id": JOB, "warning": "IMAGE_VERSION_NOT_FOUND"}
    assert transport.calls[0].path == f"/v1/users/{ID}/snapshots/{SNAP}/restore"


@pytest.mark.parametrize(
    ("status", "code", "details", "const"),
    [
        (409, "RESTORE_IN_PROGRESS", None, errcodes.RESTORE_IN_PROGRESS),
        (409, "APP_BUILDING", None, errcodes.APP_BUILDING),
        (
            400,
            "SNAPSHOT_EXCEEDS_STORAGE",
            {"required_bytes": 10, "available_bytes": 5},
            errcodes.SNAPSHOT_EXCEEDS_STORAGE,
        ),
    ],
)
def test_restore_refusals_keep_their_code(status: int, code: str, details: Any, const: str) -> None:
    transport = FakeTransport()
    transport.queue_error(status, code, details=details)
    with pytest.raises(VertraAPIError) as info:
        make(transport).snapshots.restore(ID, SNAP, "applications")
    assert info.value.code == const == code


def test_exceeds_storage_details_are_readable() -> None:
    transport = FakeTransport()
    details = {"required_bytes": 10, "available_bytes": 5, "required_ram_mb": 512}
    transport.queue_error(400, "SNAPSHOT_EXCEEDS_STORAGE", details=details)
    with pytest.raises(VertraAPIError) as info:
        make(transport).databases.create({"name": "db", "ram": 256, "snapshot_id": SNAP})
    assert info.value.snapshot_exceeds_storage == details
    assert VertraAPIError("x", status=400, code="OTHER", details=details).snapshot_exceeds_storage is None


# -- snapshot_jobs ----------------------------------------------------------


def test_jobs_list_sends_scope_kind_and_limit() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": [_job("ready")["response"]]})
    jobs = make(transport).snapshot_jobs.list(ID, "databases", kind="restore", limit=5)
    assert transport.calls[0].path == f"/v1/users/{ID}/snapshots/jobs"
    assert _query(transport) == {"scope": ["databases"], "kind": ["restore"], "limit": ["5"]}
    assert jobs[0]["status"] == "ready"


def test_jobs_list_omits_optional_query() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": []})
    make(transport).snapshot_jobs.list(ID, "applications")
    assert _query(transport) == {"scope": ["applications"]}


def test_jobs_get_sends_scope() -> None:
    transport = FakeTransport()
    transport.queue_json(_job("running"))
    job = make(transport).snapshot_jobs.get(ID, JOB, "applications")
    assert transport.calls[0].path == f"/v1/users/{ID}/snapshots/jobs/{JOB}"
    assert _query(transport) == {"scope": ["applications"]}
    assert job["status"] == "running"


def test_jobs_get_without_scope_sends_no_query() -> None:
    transport = FakeTransport()
    transport.queue_json(_job("ready"))
    make(transport).snapshot_jobs.get(ID, JOB)
    assert transport.calls[0].path == f"/v1/users/{ID}/snapshots/jobs/{JOB}"
    assert _query(transport) == {}


def test_jobs_get_takes_a_per_request_timeout() -> None:
    transport = FakeTransport()
    transport.queue_json(_job("ready"))
    make(transport).snapshot_jobs.get(ID, JOB, timeout=7)
    assert transport.calls[0].timeout == 7


def test_jobs_get_of_another_account_is_a_404() -> None:
    transport = FakeTransport()
    transport.queue_error(404, "SNAPSHOT_JOB_NOT_FOUND")
    with pytest.raises(NotFoundError):
        make(transport).snapshot_jobs.get(ID, JOB, "applications")


def test_jobs_path_params_are_encoded() -> None:
    with pytest.raises(ValueError):
        make(FakeTransport()).snapshot_jobs.get(ID, "..", "applications")


def test_wait_polls_until_ready(no_sleep: list[float]) -> None:
    transport = FakeTransport()
    for status in ("queued", "running", "ready"):
        transport.queue_json(_job(status))
    job = make(transport).snapshot_jobs.wait(ID, JOB, "applications", interval=1.5)
    assert job["status"] == "ready"
    assert len(transport.calls) == 3
    assert no_sleep == [1.5, 1.5]


def test_wait_without_scope_polls_without_query_and_passes_the_request_timeout() -> None:
    transport = FakeTransport()
    transport.queue_json(_job("running"))
    transport.queue_json(_job("ready"))
    make(transport).snapshot_jobs.wait(ID, JOB, timeout=9)
    assert [_query(transport, i) for i in (0, 1)] == [{}, {}]
    assert [c.timeout for c in transport.calls] == [9, 9]


def test_wait_raises_when_the_job_is_skipped() -> None:
    transport = FakeTransport()
    transport.queue_json(_job("skipped", reason="DATABASE_NOT_READY"))
    with pytest.raises(SnapshotJobSkippedError) as info:
        make(transport).snapshot_jobs.wait(ID, JOB, "applications")
    assert info.value.code == "DATABASE_NOT_READY"
    assert info.value.reason == "DATABASE_NOT_READY"
    assert info.value.status == "skipped"
    assert isinstance(info.value, SnapshotJobError)


def test_wait_calls_on_progress_on_every_poll_that_has_not_ended() -> None:
    progress = {"phase": "copying", "percent": 40, "done_bytes": 4, "total_bytes": 10, "eta_seconds": 3}
    transport = FakeTransport()
    transport.queue_json(_job("queued"))
    transport.queue_json(_job("running", progress=progress))
    transport.queue_json(_job("ready"))
    seen: list[Any] = []
    job = make(transport).snapshot_jobs.wait(ID, JOB, "applications", on_progress=seen.append)
    assert job["status"] == "ready"
    assert [j["status"] for j in seen] == ["queued", "running"]
    assert seen[1]["progress"] == progress


def test_wait_raises_with_the_public_reason_when_failed() -> None:
    transport = FakeTransport()
    transport.queue_json(_job("running"))
    transport.queue_json(_job("failed", reason="SNAPSHOT_CORRUPTED"))
    with pytest.raises(SnapshotJobFailedError) as info:
        make(transport).snapshot_jobs.wait(ID, JOB, "applications")
    assert info.value.code == errcodes.SNAPSHOT_CORRUPTED
    assert info.value.reason == errcodes.SNAPSHOT_CORRUPTED
    assert info.value.status == "failed"
    assert info.value.job["status"] == "failed"


def test_wait_failed_carries_the_details_of_the_reason() -> None:
    details = {"required_bytes": 10, "available_bytes": 5, "required_ram_mb": 512}
    transport = FakeTransport()
    transport.queue_json(_job("failed", reason="SNAPSHOT_EXCEEDS_STORAGE", details=details))
    with pytest.raises(SnapshotJobFailedError) as info:
        make(transport).snapshot_jobs.wait(ID, JOB, "databases")
    assert info.value.details == details
    assert info.value.snapshot_exceeds_storage == details


def test_wait_failed_without_reason_has_a_default_code() -> None:
    transport = FakeTransport()
    transport.queue_json(_job("failed"))
    with pytest.raises(SnapshotJobFailedError) as info:
        make(transport).snapshot_jobs.wait(ID, JOB, "applications")
    assert info.value.code == "SNAPSHOT_FAILED"


def test_wait_times_out_while_the_job_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [0.0]
    monkeypatch.setattr("time.monotonic", lambda: now[0])
    monkeypatch.setattr("time.sleep", lambda s: now.__setitem__(0, now[0] + s))
    transport = FakeTransport()
    transport.default_json = _job("running")
    with pytest.raises(SnapshotJobTimeoutError) as info:
        make(transport).snapshot_jobs.wait(ID, JOB, "applications", wait_timeout=10, interval=4)
    assert info.value.code == "WAIT_TIMEOUT"
    assert info.value.reason is None
    assert info.value.job["status"] == "running"
    assert len(transport.calls) == 3


def test_wait_propagates_api_errors() -> None:
    transport = FakeTransport()
    transport.queue_error(429, "RATE_LIMIT_EXCEEDED", retry_after=3)
    with pytest.raises(RateLimitError):
        make(transport).snapshot_jobs.wait(ID, JOB, "applications")


def test_snapshot_create_202_exposes_the_job_id() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"job_id": JOB}}, status=202)
    result = make(transport).snapshots.create(ID, "applications")
    assert result == {"job_id": JOB}


def test_create_and_wait_returns_the_snapshot_of_a_201() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": SNAP}}, status=201)
    assert make(transport).snapshots.create_and_wait(ID, "applications") == {"id": SNAP}
    assert len(transport.calls) == 1


def test_create_and_wait_follows_the_job_and_reads_the_snapshot_from_the_list() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"job_id": JOB}}, status=202)
    transport.queue_json(_job("running", kind="snapshot", progress={"phase": "copying"}))
    transport.queue_json(_job("ready", kind="snapshot", snapshot_id=SNAP))
    transport.queue_json({"response": [{"id": "other"}, {"id": SNAP}]})
    seen: list[str] = []
    snapshot = make(transport).snapshots.create_and_wait(
        ID, "applications", on_progress=lambda job: seen.append(job["status"])
    )
    assert snapshot == {"id": SNAP}
    assert seen == ["running"]
    assert transport.calls[1].path == f"/v1/users/{ID}/snapshots/jobs/{JOB}"
    assert transport.calls[3].path == f"/v1/users/{ID}/snapshots"


def test_create_and_wait_raises_when_the_job_fails_or_is_skipped() -> None:
    failed = FakeTransport()
    failed.queue_json({"response": {"job_id": JOB}}, status=202)
    failed.queue_json(_job("failed", kind="snapshot", reason="SNAPSHOT_TOO_LARGE", details={"max_bytes": 10}))
    with pytest.raises(SnapshotJobFailedError) as info:
        make(failed).snapshots.create_and_wait(ID, "databases")
    assert info.value.reason == "SNAPSHOT_TOO_LARGE"
    assert info.value.details == {"max_bytes": 10}
    skipped = FakeTransport()
    skipped.queue_json({"response": {"job_id": JOB}}, status=202)
    skipped.queue_json(_job("skipped", kind="snapshot", reason="DATABASE_NOT_READY"))
    with pytest.raises(SnapshotJobSkippedError):
        make(skipped).snapshots.create_and_wait(ID, "databases")


def test_create_and_wait_times_out_while_the_job_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [0.0]
    monkeypatch.setattr("time.monotonic", lambda: now[0])
    monkeypatch.setattr("time.sleep", lambda s: now.__setitem__(0, now[0] + s))
    transport = FakeTransport()
    transport.queue_json({"response": {"job_id": JOB}}, status=202)
    transport.default_json = _job("running", kind="snapshot")
    with pytest.raises(SnapshotJobTimeoutError):
        make(transport).snapshots.create_and_wait(ID, "applications", wait_timeout=10, interval=4)


# -- restore_job_id on create ----------------------------------------------


def test_app_create_from_snapshot_returns_restore_job_id() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": ID, "status": "down", "restore_job_id": JOB}}, status=202)
    app = make(transport).apps.create({"name": "a", "snapshot_id": SNAP})
    assert app["restore_job_id"] == JOB


def test_database_create_from_snapshot_returns_restore_job_id() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": ID, "restore_job_id": JOB}}, status=202)
    db = make(transport).databases.create({"name": "d", "ram": 256, "snapshot_id": SNAP})
    assert db["restore_job_id"] == JOB
    assert json.loads(transport.calls[0].body or b"")["snapshot_id"] == SNAP


# -- restore_job_id on status ------------------------------------------------


def test_status_carries_restore_job_id() -> None:
    transport = FakeTransport()
    client = make(transport)
    transport.queue_json({"response": {"id": ID, "running": False, "restore_job_id": JOB}})
    assert client.apps.status(ID)["restore_job_id"] == JOB
    transport.queue_json({"response": [{"id": ID, "restore_job_id": JOB}, {"id": SNAP, "restore_job_id": None}]})
    apps = client.apps.status_all()
    assert apps[0]["restore_job_id"] == JOB and apps[1]["restore_job_id"] is None
    transport.queue_json({"response": {"id": ID, "running": True, "restore_job_id": None}})
    assert client.databases.status(ID)["restore_job_id"] is None
    transport.queue_json({"response": [{"id": ID, "restore_job_id": JOB}]})
    assert client.databases.status_all()[0]["restore_job_id"] == JOB


# -- apps.download: a manual snapshot, then its zip --------------------------


def test_download_takes_a_snapshot_then_downloads_it() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": SNAP}}, status=201)
    transport.queue_binary(b"zip")
    assert make(transport).apps.download(ID) == b"zip"
    assert [(c.method, c.path) for c in transport.calls] == [
        ("POST", f"/v1/users/{ID}/snapshots"),
        ("GET", f"/v1/users/{ID}/snapshots/{SNAP}/download"),
    ]
    assert _query(transport, 0) == {"scope": ["applications"]}
    assert _query(transport, 1) == {"scope": ["applications"]}


def test_download_waits_for_the_job_of_a_202(no_sleep: list[float]) -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"job_id": JOB}}, status=202)
    transport.queue_json(_job("running", kind="snapshot"))
    transport.queue_json(_job("ready", kind="snapshot", snapshot_id=SNAP))
    transport.queue_json({"response": [{"id": SNAP}]})
    transport.queue_binary(b"zip")
    seen: list[str] = []
    data = make(transport).apps.download(ID, interval=1.0, on_progress=lambda job: seen.append(job["status"]))
    assert data == b"zip"
    assert seen == ["running"]
    assert transport.calls[-1].path == f"/v1/users/{ID}/snapshots/{SNAP}/download"
    assert no_sleep == [1.0]


def test_download_does_not_use_the_old_route_or_download_id() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": SNAP}}, status=201)
    transport.queue_binary(b"zip")
    make(transport).apps.download(ID)
    assert all("/v1/apps/" not in c.path for c in transport.calls)
    with pytest.raises(TypeError):
        make(transport).apps.download(ID, download_id="dl-1")  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        make(transport).apps.download(ID, wait=False)  # type: ignore[call-arg]


def test_download_timeout_is_per_request_and_wait_timeout_is_the_total() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": SNAP}}, status=201)
    transport.queue_binary(b"zip")
    make(transport).apps.download(ID, timeout=77)
    assert [c.timeout for c in transport.calls] == [77, 77]


def test_download_gives_up_when_the_snapshot_job_runs_past_wait_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [0.0]
    monkeypatch.setattr("time.monotonic", lambda: now[0])
    monkeypatch.setattr("time.sleep", lambda s: now.__setitem__(0, now[0] + s))
    transport = FakeTransport()
    transport.queue_json({"response": {"job_id": JOB}}, status=202)
    transport.default_json = _job("running", kind="snapshot")
    with pytest.raises(SnapshotJobTimeoutError):
        make(transport).apps.download(ID, wait_timeout=5, interval=3)


def test_download_propagates_the_refusals_of_the_snapshot() -> None:
    transport = FakeTransport()
    transport.queue_error(
        429, "SNAPSHOT_RATE_LIMITED", details={"scope": "account", "retry_after": 60, "resets_at": "x"}
    )
    with pytest.raises(RateLimitError) as info:
        make(transport).apps.download(ID)
    assert info.value.retry_after == 60
    transport.queue_error(403, "PLAN_NOT_ALLOWED")
    with pytest.raises(VertraAPIError):
        make(transport).apps.download(ID)
    transport.queue_json({"response": {"id": SNAP}}, status=201)
    transport.queue_error(404, "SNAPSHOT_NOT_FOUND")
    with pytest.raises(NotFoundError):
        make(transport).apps.download(ID)


def test_create_and_wait_passes_the_request_timeout_to_every_call() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"job_id": JOB}}, status=202)
    transport.queue_json(_job("ready", kind="snapshot", snapshot_id=SNAP))
    transport.queue_json({"response": [{"id": SNAP}]})
    make(transport).snapshots.create_and_wait(ID, "applications", timeout=44)
    assert [c.timeout for c in transport.calls] == [44, 44, 44]
