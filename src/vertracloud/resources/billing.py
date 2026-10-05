"""`billing` domain — 7 routes (scopes `billing:read/write`, `redeem:write`)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..client import encode_path_param
from ..types import (
    APIBillingDetails,
    APIOrderCreateResponse,
    APIOrderListItem,
    APIOrderStatus,
    APIPixPaymentResponse,
    APIRedeemResponse,
    CreateOrderBody,
    OrderProvider,
    PutBillingDetailsBody,
)

if TYPE_CHECKING:
    from ..client import VertraClient


class BillingOrdersResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(self, *, provider: OrderProvider | None = None) -> list[APIOrderListItem]:
        """GET /v1/orders — scope `billing:read`. Query `provider?: pix|card|redeem_code`."""
        return self._c.request_json("GET", "/v1/orders", query={"provider": provider})

    def status(self, order_id: str) -> APIOrderStatus:
        """GET /v1/orders/:orderId/status — scope `billing:read`."""
        return self._c.request_json("GET", f"/v1/orders/{encode_path_param(order_id)}/status")

    def create(self, body: CreateOrderBody) -> APIOrderCreateResponse:
        """POST /v1/orders — scope `billing:write`."""
        return self._c.request_json("POST", "/v1/orders", json_body=body)

    def initiate_pix(self, order_id: str) -> APIPixPaymentResponse:
        """POST /v1/orders/:orderId/initiate/pix — scope `billing:write`."""
        return self._c.request_json("POST", f"/v1/orders/{encode_path_param(order_id)}/initiate/pix")


class BillingResource:
    """`billing.*` — `orders`, `details`, `update_details`, `redeem`."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client
        self.orders = BillingOrdersResource(client)

    def redeem(self, code: str) -> APIRedeemResponse:
        """POST /v1/redeem/:code — scope `redeem:write`."""
        return self._c.request_json("POST", f"/v1/redeem/{encode_path_param(code)}")

    def details(self) -> APIBillingDetails | None:
        """GET /v1/users/me/billing — scope `billing:read`. `None` until details are saved."""
        return self._c.request_json("GET", "/v1/users/me/billing")

    def update_details(self, body: PutBillingDetailsBody) -> APIBillingDetails:
        """PUT /v1/users/me/billing — scope `billing:write`. Replaces the details; complete before `orders.create`."""
        return self._c.request_json("PUT", "/v1/users/me/billing", json_body=body)
