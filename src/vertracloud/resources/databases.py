"""`databases` domain — 13 routes (scopes `databases:read/write/delete/credentials`)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..client import encode_path_param
from ..types import (
    APIDatabase,
    APIDatabaseCertificate,
    APIDatabasePasswordReset,
    APIDatabaseStatus,
    APIDatabaseStatusShort,
    APIOperationResponse,
    CreateDatabaseBody,
    UpdateDatabaseBody,
)

if TYPE_CHECKING:
    from ..client import VertraClient


class DatabaseCertificateResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def get(
        self, db_id: str, *, workspace_id: str | None = None, timeout: float | None = None
    ) -> APIDatabaseCertificate:
        """GET /v1/databases/:id/credentials/certificate — scope `databases:credentials`."""
        return self._c.request_json(
            "GET",
            f"/v1/databases/{encode_path_param(db_id)}/credentials/certificate",
            query={"workspace_id": workspace_id},
            timeout=timeout,
        )

    def reset(self, db_id: str, *, workspace_id: str | None = None) -> None:
        """POST /v1/databases/:id/credentials/certificate/reset — scope `databases:credentials`."""
        return self._c.request_json(
            "POST",
            f"/v1/databases/{encode_path_param(db_id)}/credentials/certificate/reset",
            query={"workspace_id": workspace_id},
        )


class DatabasePasswordResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def reset(self, db_id: str, *, workspace_id: str | None = None) -> APIDatabasePasswordReset:
        """POST /v1/databases/:id/credentials/reset — scope `databases:credentials`."""
        return self._c.request_json(
            "POST", f"/v1/databases/{encode_path_param(db_id)}/credentials/reset", query={"workspace_id": workspace_id}
        )


class DatabaseCredentialsResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client
        self.certificate = DatabaseCertificateResource(client)
        self.password = DatabasePasswordResource(client)


class DatabasesResource:
    """`databases.*` — statusAll/get/status/metrics/create/update/start/stop/reset/delete +
    `credentials`."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client
        self.credentials = DatabaseCredentialsResource(client)

    def status_all(self, *, workspace_id: str | None = None) -> list[APIDatabaseStatusShort]:
        """GET /v1/databases/status — scope `databases:read`."""
        return self._c.request_json("GET", "/v1/databases/status", query={"workspace_id": workspace_id})

    def get(self, db_id: str, *, workspace_id: str | None = None) -> APIDatabase:
        """GET /v1/databases/:id — scope `databases:read`."""
        return self._c.request_json(
            "GET", f"/v1/databases/{encode_path_param(db_id)}", query={"workspace_id": workspace_id}
        )

    def status(self, db_id: str, *, workspace_id: str | None = None) -> APIDatabaseStatus:
        """GET /v1/databases/:id/status — scope `databases:read`."""
        return self._c.request_json(
            "GET", f"/v1/databases/{encode_path_param(db_id)}/status", query={"workspace_id": workspace_id}
        )

    def metrics(self, db_id: str, *, workspace_id: str | None = None) -> list[Any]:
        """GET /v1/databases/:id/metrics — scope `databases:read`. JSON, not SSE."""
        return self._c.request_json(
            "GET", f"/v1/databases/{encode_path_param(db_id)}/metrics", query={"workspace_id": workspace_id}
        )

    def create(self, body: CreateDatabaseBody) -> APIDatabase:
        """POST /v1/databases — scope `databases:write`."""
        return self._c.request_json("POST", "/v1/databases", json_body=body)

    def update(self, db_id: str, body: UpdateDatabaseBody, *, workspace_id: str | None = None) -> APIDatabase:
        """PUT /v1/databases/:id — scope `databases:write`."""
        return self._c.request_json(
            "PUT", f"/v1/databases/{encode_path_param(db_id)}", json_body=body, query={"workspace_id": workspace_id}
        )

    def start(self, db_id: str, *, workspace_id: str | None = None) -> APIOperationResponse:
        """POST /v1/databases/:id/start — scope `databases:write`."""
        return self._c.request_json(
            "POST", f"/v1/databases/{encode_path_param(db_id)}/start", query={"workspace_id": workspace_id}
        )

    def stop(self, db_id: str, *, workspace_id: str | None = None) -> APIOperationResponse:
        """POST /v1/databases/:id/stop — scope `databases:write`."""
        return self._c.request_json(
            "POST", f"/v1/databases/{encode_path_param(db_id)}/stop", query={"workspace_id": workspace_id}
        )

    def reset(self, db_id: str, *, workspace_id: str | None = None) -> None:
        """POST /v1/databases/:id/reset — scope `databases:write`."""
        return self._c.request_json(
            "POST", f"/v1/databases/{encode_path_param(db_id)}/reset", query={"workspace_id": workspace_id}
        )

    def delete(self, db_id: str, *, workspace_id: str | None = None) -> None:
        """DELETE /v1/databases/:id — scope `databases:delete`."""
        return self._c.request_json(
            "DELETE", f"/v1/databases/{encode_path_param(db_id)}", query={"workspace_id": workspace_id}
        )
