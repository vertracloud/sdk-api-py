"""`plans` domain — the plan catalog (public route, no API key)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..types import APIPlansCatalog

if TYPE_CHECKING:
    from ..client import VertraClient


class PlansResource:
    """`plans.*` — `list`."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(self) -> APIPlansCatalog:
        """GET /v1/plans — no authentication (sent without the API key). The plans currently for sale, the
        billing periods with their discounts (`cycles`: 1, 3, 6 or 12 months) and, per plan, price, memory, vCPU,
        limits and features."""
        return self._c.request_json("GET", "/v1/plans", auth=False)
