from __future__ import annotations

import json
from typing import get_args

from vertracloud import VertraClient
from vertracloud.resources.plans import PlansResource
from vertracloud.types import (
    APIOrderQuote,
    APIPlansCatalog,
    BillingMonths,
    LegacyPlanName,
    UserPlanName,
    V3PlanName,
)

from .fake_transport import FakeTransport


def _client(transport: FakeTransport) -> VertraClient:
    return VertraClient(api_key="secret-key", transport=transport)


def test_plans_list_is_public_and_unwraps_the_envelope() -> None:
    transport = FakeTransport()
    catalog: APIPlansCatalog = {
        "grid": "v3",
        "cycles": [{"months": 1, "discount_percent": 0}, {"months": 6, "discount_percent": 15}],
        "plans": [],
    }
    transport.queue_json({"response": catalog})
    client = _client(transport)
    assert isinstance(client.plans, PlansResource)
    assert client.plans.list() == catalog
    call = transport.calls[0]
    assert call.method == "GET"
    assert call.url == "https://api.vertracloud.app/v1/plans"
    assert "Authorization" not in call.headers
    assert call.headers["User-Agent"].startswith("vertracloud-sdk-py/")
    assert call.body is None


def test_other_routes_still_send_the_api_key() -> None:
    transport = FakeTransport()
    _client(transport).account.get()
    assert transport.calls[0].headers["Authorization"] == "Bearer secret-key"


def test_orders_quote_posts_the_body_and_returns_the_quote() -> None:
    transport = FakeTransport()
    quote: APIOrderQuote = {
        "plan": "starter-1",
        "months": 6,
        "list_price": 100,
        "period_discount_percent": 15,
        "coupon": None,
        "total": 85,
        "legacy_price": False,
        "legacy_price_until": None,
        "payment_methods": ["pix", "card"],
    }
    transport.queue_json({"response": quote})
    client = _client(transport)
    assert client.billing.orders.quote({"plan": "starter-1", "months": 6, "coupon": "V3-X"}) == quote
    call = transport.calls[0]
    assert (call.method, call.path) == ("POST", "/v1/orders/quote")
    assert json.loads(call.body or b"") == {"plan": "starter-1", "months": 6, "coupon": "V3-X"}
    assert call.headers["Authorization"] == "Bearer secret-key"
    assert call.headers["Content-Type"] == "application/json"


def test_plan_names_cover_both_grids() -> None:
    v3 = set(get_args(V3PlanName))
    legacy = set(get_args(LegacyPlanName))
    assert len(get_args(V3PlanName)) == 22
    assert {"starter-1", "starter-2", "pro-4", "business-24", "enterprise-512"} <= v3
    assert {"economy", "pro", "scale", "intermediary", "enterprise-4", "enterprise-30"} <= legacy
    assert set(get_args(UserPlanName)) == v3 | legacy
    assert get_args(BillingMonths) == (1, 3, 6, 12)
