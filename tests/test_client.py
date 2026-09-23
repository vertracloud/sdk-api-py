"""Client core: auth header, envelope, path encoding, query params, timeout,
and the secret never leaking through an error or repr."""

from __future__ import annotations

import json

import pytest

from vertracloud import VertraClient
from vertracloud.errors import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ScopeDeniedError,
    ValidationError,
    VertraAPIError,
)
from vertracloud.transport import Response

from .fake_transport import FakeTransport


def make_client(transport: FakeTransport, **kwargs) -> VertraClient:
    return VertraClient(api_key="super-secret-key", transport=transport, **kwargs)


def test_authorization_header_is_bearer() -> None:
    transport = FakeTransport()
    client = make_client(transport)
    client.apps.get("app-1")
    assert transport.calls[0].headers["Authorization"] == "Bearer super-secret-key"


def test_default_base_url_and_user_agent() -> None:
    transport = FakeTransport()
    client = make_client(transport)
    client.apps.get("app-1")
    call = transport.calls[0]
    assert call.url.startswith("https://api.vertracloud.app/v1/apps/app-1")
    assert call.headers["User-Agent"].startswith("vertracloud-sdk-py/")


def test_custom_base_url_timeout_and_user_agent() -> None:
    transport = FakeTransport()
    client = make_client(transport, base_url="https://staging.example.com/", timeout=5, user_agent="my-agent/1.0")
    client.apps.get("app-1")
    call = transport.calls[0]
    assert call.url == "https://staging.example.com/v1/apps/app-1"
    assert call.timeout == 5
    assert call.headers["User-Agent"] == "my-agent/1.0"


def test_envelope_success_is_unwrapped() -> None:
    transport = FakeTransport()
    transport.queue_json({"response": {"id": "app-1", "name": "x"}})
    client = make_client(transport)
    result = client.apps.get("app-1")
    assert result == {"id": "app-1", "name": "x"}


def test_path_params_are_percent_encoded() -> None:
    transport = FakeTransport()
    client = make_client(transport)
    client.apps.get("weird id/with?stuff")
    assert transport.calls[0].path == "/v1/apps/weird%20id%2Fwith%3Fstuff"


def test_query_params_only_when_defined_and_booleans_as_strings() -> None:
    transport = FakeTransport()
    client = make_client(transport)
    client.apps.files.upload("app-1", file=b"data", filename="a.py", restart=True)
    call = transport.calls[0]
    assert "restart=true" in call.url
    assert "workspace_id" not in call.url

    transport2 = FakeTransport()
    client2 = make_client(transport2)
    client2.apps.get("app-1", workspace_id="ws-1")
    assert "workspace_id=ws-1" in transport2.calls[0].url


@pytest.mark.parametrize(
    ("status", "code", "expected_cls"),
    [
        (401, "API_KEY_INVALID", AuthenticationError),
        (403, "API_KEY_SCOPE_DENIED", ScopeDeniedError),
        (404, "APP_NOT_FOUND", NotFoundError),
        (400, "INVALID_BODY", ValidationError),
        (422, "INVALID_BODY", ValidationError),
        (500, "INTERNAL_SERVER_ERROR", VertraAPIError),
    ],
)
def test_error_status_maps_to_typed_exception(status: int, code: str, expected_cls: type[Exception]) -> None:
    transport = FakeTransport()
    transport.queue_error(status, code, message="boom", details={"required": "apps:write"})
    client = make_client(transport)
    with pytest.raises(expected_cls) as exc_info:
        client.apps.get("app-1")
    err = exc_info.value
    assert isinstance(err, VertraAPIError)
    assert err.status == status
    assert err.code == code
    assert err.details == {"required": "apps:write"}


def test_rate_limit_error_exposes_retry_after_from_body() -> None:
    transport = FakeTransport()
    transport.queue_error(429, "RATE_LIMIT_EXCEEDED", retry_after=12)
    client = make_client(transport)
    with pytest.raises(RateLimitError) as exc_info:
        client.apps.get("app-1")
    assert exc_info.value.retry_after == 12.0


def test_rate_limit_error_falls_back_to_retry_after_header() -> None:
    transport = FakeTransport()
    transport.queue(
        Response(status=429, headers={"retry-after": "7"}, body=json.dumps({"code": "DAILY_QUOTA_EXCEEDED"}).encode())
    )
    client = make_client(transport)
    with pytest.raises(RateLimitError) as exc_info:
        client.apps.get("app-1")
    assert exc_info.value.retry_after == 7.0
    assert exc_info.value.code == "DAILY_QUOTA_EXCEEDED"


def test_error_never_leaks_api_key_in_str_or_repr() -> None:
    transport = FakeTransport()
    transport.queue_error(403, "API_KEY_SCOPE_DENIED", details={"required": "apps:write"})
    client = make_client(transport)
    try:
        client.apps.get("app-1")
    except VertraAPIError as err:
        assert "super-secret-key" not in str(err)
        assert "super-secret-key" not in repr(err)
    else:
        raise AssertionError("expected VertraAPIError")


def test_client_repr_never_leaks_api_key() -> None:
    transport = FakeTransport()
    client = make_client(transport)
    assert "super-secret-key" not in repr(client)
    assert "super-secret-key" not in str(client)


def test_no_automatic_retry_on_rate_limit() -> None:
    transport = FakeTransport()
    transport.queue_error(429, "RATE_LIMIT_EXCEEDED", retry_after=1)
    client = make_client(transport)
    with pytest.raises(RateLimitError):
        client.apps.get("app-1")
    assert len(transport.calls) == 1


def test_missing_api_key_raises() -> None:
    with pytest.raises(ValueError):
        VertraClient(api_key="")
