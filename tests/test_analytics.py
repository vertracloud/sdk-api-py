from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest

from vertracloud import VertraClient, errcodes
from vertracloud.errors import ScopeDeniedError, ValidationError, VertraAPIError

from .fake_transport import FakeTransport


def _client(transport: FakeTransport) -> VertraClient:
    return VertraClient(api_key="secret-key", transport=transport)


def _query(transport: FakeTransport, index: int = 0) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(transport.calls[index].url).query).items()}


def _request(request_id: str) -> dict[str, Any]:
    return {"time": "2026-11-03T12:00:00.000Z", "request_id": request_id, "path": "/", "status": 200}


def _page(ids: list[str], cursor: str | None) -> dict[str, Any]:
    return {"response": {"order": "desc", "requests": [_request(i) for i in ids], "cursor": cursor}}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (["country", "path"], "country,path"),
        (("device",), "device"),
        ([], ""),
        ("", ""),
        ("country,path", "country,path"),
    ],
)
def test_traffic_breakdowns_accepts_string_or_sequence(value: Any, expected: str) -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {}})
    _client(transport).apps.analytics.traffic("a", breakdowns=value)
    assert parse_qs(urlparse(transport.calls[0].url).query, keep_blank_values=True)["breakdowns"] == [expected]


def test_traffic_without_breakdowns_omits_the_param() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {}})
    _client(transport).apps.analytics.traffic("a")
    assert "breakdowns" not in transport.calls[0].url


def test_traffic_sends_window_filters_and_workspace_and_unwraps() -> None:
    transport = FakeTransport()
    body = {"web_published": False, "hosts": [], "summary": None, "series": [], "previous": None, "breakdowns": {}}
    transport.queue_json({"response": body})
    result = _client(transport).apps.analytics.traffic(
        "app-1",
        start="2026-11-02T00:00:00Z",
        compare=True,
        breakdowns="country,path",
        status="5xx",
        referer="(none)",
        limit=5,
        workspace_id="ws-1",
    )
    assert result == body  # type: ignore[comparison-overlap]
    call = transport.calls[0]
    assert call.method == "GET"
    assert call.path == "/v1/apps/app-1/analytics"
    assert call.headers["Authorization"] == "Bearer secret-key"
    assert _query(transport) == {
        "start": "2026-11-02T00:00:00Z",
        "compare": "true",
        "breakdowns": "country,path",
        "status": "5xx",
        "referer": "(none)",
        "limit": "5",
        "workspace_id": "ws-1",
    }


def test_errors_performance_and_requests_hit_their_own_path() -> None:
    transport = FakeTransport()
    analytics = _client(transport).apps.analytics
    analytics.errors("a", include_4xx=True)
    analytics.performance("a", asn="28573", compare=False)
    analytics.requests("a", order="asc", limit=100, cursor="abc", path="/api")
    assert [c.path for c in transport.calls] == [
        "/v1/apps/a/analytics/errors",
        "/v1/apps/a/analytics/performance",
        "/v1/apps/a/analytics/requests",
    ]
    assert _query(transport, 0) == {"include_4xx": "true"}
    assert _query(transport, 1) == {"asn": "28573", "compare": "false"}
    assert _query(transport, 2) == {"order": "asc", "limit": "100", "cursor": "abc", "path": "/api"}


def test_compare_start_is_sent_on_traffic_errors_and_performance() -> None:
    transport = FakeTransport()
    analytics = _client(transport).apps.analytics
    analytics.traffic("a", compare_start="2026-10-26T00:00:00Z")
    analytics.errors("a", compare_start="2026-10-26T00:00:00Z", compare=True)
    analytics.performance("a", compare_start="2026-10-26T00:00:00Z")
    for index in range(3):
        assert _query(transport, index)["compare_start"] == "2026-10-26T00:00:00Z"
    assert _query(transport, 1)["compare"] == "true"


def test_app_id_is_one_path_segment() -> None:
    transport = FakeTransport()
    _client(transport).apps.analytics.traffic("a b")
    assert transport.calls[0].path == "/v1/apps/a%20b/analytics"


def test_iter_requests_follows_the_cursor_with_a_pinned_window() -> None:
    transport = FakeTransport()
    transport.queue_json(_page(["r1", "r2"], "c1"))
    transport.queue_json(_page(["r3"], None))
    ids = [r["request_id"] for r in _client(transport).apps.analytics.iter_requests("a", limit=2, bot="(none)")]
    assert ids == ["r1", "r2", "r3"]
    assert len(transport.calls) == 2
    first, second = _query(transport, 0), _query(transport, 1)
    assert "cursor" not in first
    assert second["cursor"] == "c1"
    assert first["start"] == second["start"] and first["end"] == second["end"]
    assert second["bot"] == "(none)" and second["limit"] == "2"


def test_iter_requests_keeps_the_window_given() -> None:
    transport = FakeTransport()
    transport.queue_json(_page([], None))
    list(_client(transport).apps.analytics.iter_requests("a", start="2026-11-01T00:00:00Z", end="2026-11-02T00:00:00Z"))
    assert _query(transport) == {"start": "2026-11-01T00:00:00Z", "end": "2026-11-02T00:00:00Z"}


def test_plan_errors_map_to_scope_denied_with_the_code() -> None:
    transport = FakeTransport()
    transport.queue_error(403, errcodes.PLAN_DOES_NOT_SUPPORT_WEB_ANALYTICS_REQUESTS, message="no")
    with pytest.raises(ScopeDeniedError) as info:
        _client(transport).apps.analytics.requests("a")
    assert info.value.code == "PLAN_DOES_NOT_SUPPORT_WEB_ANALYTICS_REQUESTS"
    assert info.value.analytics_range is None


def test_range_and_busy_details_have_readers() -> None:
    transport = FakeTransport()
    details = {"history_days": 7, "earliest": "2026-10-27T00:00:00.000Z"}
    transport.queue_error(400, errcodes.ANALYTICS_RANGE_EXCEEDS_PLAN, details=details)
    with pytest.raises(ValidationError) as info:
        _client(transport).apps.analytics.traffic("a", start="2026-01-01T00:00:00Z")
    assert info.value.analytics_range == details
    assert info.value.analytics_retry_after is None

    transport.queue_error(503, errcodes.ANALYTICS_BUSY, details={"retry_after": 60})
    with pytest.raises(VertraAPIError) as busy:
        _client(transport).apps.analytics.traffic("a")
    assert busy.value.status == 503
    assert busy.value.analytics_retry_after == 60
    assert busy.value.analytics_range is None
