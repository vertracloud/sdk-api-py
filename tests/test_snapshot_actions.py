"""Destructive actions (delete, reset, restore): they run right away; timeouts and errors of the snapshot calls."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from vertracloud import RateLimitError, VertraClient, errcodes

from .fake_transport import FakeTransport

ID = "11111111-1111-1111-1111-111111111111"
SNAP = "22222222-2222-2222-2222-222222222222"


def make(transport: FakeTransport, **kwargs: Any) -> VertraClient:
    return VertraClient(api_key="k", transport=transport, **kwargs)


def _query(transport: FakeTransport) -> dict[str, list[str]]:
    return parse_qs(urlparse(transport.calls[-1].url).query)


def _body(transport: FakeTransport) -> Any:
    raw = transport.calls[-1].body
    return json.loads(raw) if raw else None


def test_app_delete_sends_only_the_workspace_and_returns_nothing() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": None})
    result = make(transport).apps.delete(ID, workspace_id=SNAP)
    assert transport.calls[-1].method == "DELETE"
    assert _query(transport) == {"workspace_id": [SNAP]}
    assert _body(transport) is None
    assert result is None


def test_database_delete_returns_the_id() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": ID})
    result = make(transport).databases.delete(ID)
    assert _query(transport) == {}
    assert _body(transport) is None
    assert result == ID


def test_database_reset_sends_no_body_and_returns_the_status() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"status": "success"}})
    result = make(transport).databases.reset(ID)
    assert _body(transport) is None
    assert result == {"status": "success"}


def test_restore_returns_the_job_and_the_warning() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"job_id": "job-1", "warning": "IMAGE_VERSION_NOT_FOUND"}})
    result = make(transport).snapshots.restore(ID, SNAP, "applications", restore_image_version=True)
    assert _body(transport) == {"restore_image_version": True}
    assert result == {"job_id": "job-1", "warning": "IMAGE_VERSION_NOT_FOUND"}


def test_restore_without_the_option_sends_an_empty_body() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"job_id": "job-1"}})
    result = make(transport).snapshots.restore(ID, SNAP, "databases")
    assert _body(transport) == {}
    assert result == {"job_id": "job-1"}


def test_creating_a_snapshot_waits_longer_than_95_seconds_and_accepts_a_timeout() -> None:
    transport = FakeTransport()
    make(transport).snapshots.create(ID, "applications")
    assert transport.calls[-1].timeout > 95
    make(transport, timeout=300).snapshots.create(ID, "applications")
    assert transport.calls[-1].timeout == 300
    make(transport).snapshots.create(ID, "applications", timeout=200)
    assert transport.calls[-1].timeout == 200


@pytest.mark.parametrize(
    "call",
    [
        lambda c, **kw: c.snapshots.restore(ID, SNAP, "applications", **kw),
        lambda c, **kw: c.apps.delete(ID, **kw),
        lambda c, **kw: c.databases.delete(ID, **kw),
        lambda c, **kw: c.databases.reset(ID, **kw),
    ],
)
def test_the_other_actions_keep_the_client_timeout_and_accept_a_per_call_one(call: Callable[..., Any]) -> None:
    transport = FakeTransport()
    call(make(transport))
    assert transport.calls[-1].timeout == 30
    call(make(transport, timeout=300))
    assert transport.calls[-1].timeout == 300
    call(make(transport), timeout=200)
    assert transport.calls[-1].timeout == 200


def test_snapshot_rate_limited_reads_retry_after_from_details() -> None:
    transport = FakeTransport()
    transport.queue_error(
        429,
        errcodes.SNAPSHOT_RATE_LIMITED,
        details={"scope": "resource", "retry_after": 42},
    )
    with pytest.raises(RateLimitError) as info:
        make(transport).snapshots.create(ID, "applications")
    assert info.value.retry_after == 42.0
    assert info.value.details["scope"] == "resource"


def test_top_level_retry_after_wins_over_details() -> None:
    transport = FakeTransport()
    transport.queue_error(429, "RATE_LIMITED", details={"retry_after": 5}, retry_after=9)
    with pytest.raises(RateLimitError) as info:
        make(transport).apps.get(ID)
    assert info.value.retry_after == 9.0


def test_restore_cooldown_reads_retry_after_from_details_and_the_header() -> None:
    transport = FakeTransport()
    transport.queue_error(429, errcodes.RESTORE_COOLDOWN, details={"retry_after": 120})
    with pytest.raises(RateLimitError) as info:
        make(transport).snapshots.restore(ID, SNAP, "applications")
    assert info.value.code == "RESTORE_COOLDOWN"
    assert info.value.retry_after == 120.0
    transport.queue_error(429, errcodes.RESTORE_COOLDOWN, headers={"retry-after": "30"})
    with pytest.raises(RateLimitError) as header:
        make(transport).snapshots.restore(ID, SNAP, "applications")
    assert header.value.retry_after == 30.0


def test_workspace_invites_disabled_is_not_a_constant() -> None:
    assert not hasattr(errcodes, "WORKSPACE_INVITES_DISABLED")


def test_new_error_codes_are_constants() -> None:
    assert errcodes.DATABASE_NOT_READY == "DATABASE_NOT_READY"
    assert errcodes.SNAPSHOT_FAILED == "SNAPSHOT_FAILED"
    assert errcodes.SNAPSHOT_TIMEOUT == "SNAPSHOT_TIMEOUT"
    assert errcodes.FILE_TOO_LARGE == "FILE_TOO_LARGE"
