"""`snapshots` domain — 5 routes, under `/v1/users/:id/snapshots` (scopes `snapshots:read/write`).

`scope` (`"applications"` or `"databases"`) is a **required** query parameter on all 5 routes —
without it the API responds 400 `INVALID_QUERY`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..client import encode_path_param
from ..types import (
    APIGroupedResourceSnapshots,
    APIResourceSnapshot,
    APISnapshotRestoreResponse,
    SnapshotScope,
)

if TYPE_CHECKING:
    from ..client import VertraClient


class SnapshotsResource:
    """`snapshots.*` — listAll/list/download/create/restore."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list_all(self, scope: SnapshotScope) -> list[APIGroupedResourceSnapshots]:
        """GET /v1/users/snapshots — scope `snapshots:read`."""
        return self._c.request_json("GET", "/v1/users/snapshots", query={"scope": scope})

    def list(self, resource_id: str, scope: SnapshotScope) -> list[APIResourceSnapshot]:
        """GET /v1/users/:id/snapshots — scope `snapshots:read`. `:id` is the app/database, not the user."""
        return self._c.request_json(
            "GET", f"/v1/users/{encode_path_param(resource_id)}/snapshots", query={"scope": scope}
        )

    def download(
        self, resource_id: str, snapshot_id: str, scope: SnapshotScope, *, timeout: float | None = None
    ) -> bytes:
        """GET /v1/users/:id/snapshots/:snapshot_id/download — scope `snapshots:read`. Zip file."""
        return self._c.request_binary(
            "GET",
            f"/v1/users/{encode_path_param(resource_id)}/snapshots/{encode_path_param(snapshot_id)}/download",
            query={"scope": scope},
            timeout=timeout,
        )

    def create(self, resource_id: str, scope: SnapshotScope) -> APIResourceSnapshot:
        """POST /v1/users/:id/snapshots — scope `snapshots:write`."""
        return self._c.request_json(
            "POST",
            f"/v1/users/{encode_path_param(resource_id)}/snapshots",
            json_body={},
            query={"scope": scope},
        )

    def restore(self, resource_id: str, snapshot_id: str, scope: SnapshotScope) -> APISnapshotRestoreResponse:
        """POST /v1/users/:id/snapshots/:snapshot_id/restore — scope `snapshots:write`."""
        return self._c.request_json(
            "POST",
            f"/v1/users/{encode_path_param(resource_id)}/snapshots/{encode_path_param(snapshot_id)}/restore",
            json_body={},
            query={"scope": scope},
        )
