"""Empty ids, `.` and `..` (also percent-encoded) never reach the transport."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from vertracloud import VertraClient
from vertracloud.client import encode_path_param

from .fake_transport import FakeTransport

INVALID = ["", ".", "..", "%2e%2e", "%2E.", ".%2e", "%2e", "%252e%252e"]


@pytest.mark.parametrize("bad", INVALID)
def test_encode_path_param_rejects_dot_segments(bad: str) -> None:
    with pytest.raises(ValueError):
        encode_path_param(bad)


def test_encode_path_param_keeps_encoding_everything_else() -> None:
    assert encode_path_param("a b/c") == "a%20b%2Fc"
    assert encode_path_param("..a") == "..a"
    assert encode_path_param("a.b") == "a.b"
    assert encode_path_param("%zz") == "%25zz"


def test_domains_remove_dot_dot_does_not_delete_the_app() -> None:
    transport = FakeTransport()
    client = VertraClient(api_key="k", transport=transport)
    with pytest.raises(ValueError):
        client.apps.domains.remove("abc", "..")
    assert transport.calls == []


CASES: list[tuple[str, Callable[[VertraClient], Any]]] = [
    ("domains.dns", lambda c: c.apps.domains.dns("abc", "..")),
    ("domains.update", lambda c: c.apps.domains.update("abc", ".", {})),
    ("domains.remove empty", lambda c: c.apps.domains.remove("abc", "")),
    ("domains.remove encoded", lambda c: c.apps.domains.remove("abc", "%2e%2e")),
    ("domains.connect", lambda c: c.apps.domains.connect("abc", "%2E.")),
    ("apps.get", lambda c: c.apps.get("..")),
    ("apps.delete", lambda c: c.apps.delete("..")),
    ("apps.envs.delete", lambda c: c.apps.envs.delete("abc", "..")),
    ("databases.get", lambda c: c.databases.get("..")),
    ("databases.delete", lambda c: c.databases.delete(".")),
    ("workspaces.delete", lambda c: c.workspaces.delete("..")),
    ("workspaces.members.remove", lambda c: c.workspaces.members.remove("ws", "..")),
    ("account.folders.delete", lambda c: c.account.folders.delete("..")),
    ("billing.orders.status", lambda c: c.billing.orders.status("..")),
]


@pytest.mark.parametrize("call", [c for _, c in CASES], ids=[n for n, _ in CASES])
def test_invalid_id_fails_before_any_request(call: Callable[[VertraClient], Any]) -> None:
    transport = FakeTransport()
    client = VertraClient(api_key="k", transport=transport)
    with pytest.raises(ValueError):
        call(client)
    assert transport.calls == []
