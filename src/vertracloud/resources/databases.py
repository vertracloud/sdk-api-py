"""`databases` domain — 14 routes (scopes `databases:read/write/delete/credentials`)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..client import encode_path_param
from ..types import (
    APIDatabase,
    APIDatabaseCertificate,
    APIDatabaseCertificateReset,
    APIDatabaseCreated,
    APIDatabaseMetrics,
    APIDatabasePasswordReset,
    APIDatabaseReset,
    APIDatabaseStatus,
    APIDatabaseStatusShort,
    APIDatabaseVersions,
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

    def reset(self, db_id: str, *, workspace_id: str | None = None) -> APIDatabaseCertificateReset:
        """POST /v1/databases/:id/credentials/certificate/reset — scope `databases:credentials`. Besides the new
        certificate, the answer lists the apps of stacks connected to the database that must restart to read it
        (`restart_required`, `apps_to_restart`). On a database with `legacy_host: True` the new certificate moves it to
        the current address, which is done only from the dashboard: with an API key this call fails with 403
        `WEBSITE_ONLY`."""
        return self._c.request_json(
            "POST",
            f"/v1/databases/{encode_path_param(db_id)}/credentials/certificate/reset",
            query={"workspace_id": workspace_id},
        )


class DatabasePasswordResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def reset(self, db_id: str, *, workspace_id: str | None = None) -> APIDatabasePasswordReset:
        """POST /v1/databases/:id/credentials/reset — scope `databases:credentials`. The answer also lists the apps
        of stacks connected to the database that must restart to read the new password (`restart_required`,
        `apps_to_restart`)."""
        return self._c.request_json(
            "POST", f"/v1/databases/{encode_path_param(db_id)}/credentials/reset", query={"workspace_id": workspace_id}
        )


class DatabaseCredentialsResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client
        self.certificate = DatabaseCertificateResource(client)
        self.password = DatabasePasswordResource(client)


class DatabasesResource:
    """`databases.*` — status_all/versions/get/status/metrics/create/update/start/stop/reset/delete +
    `credentials`."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client
        self.credentials = DatabaseCredentialsResource(client)

    def status_all(self, *, workspace_id: str | None = None) -> list[APIDatabaseStatusShort]:
        """GET /v1/databases/status — scope `databases:read`."""
        return self._c.request_json("GET", "/v1/databases/status", query={"workspace_id": workspace_id})

    def versions(self) -> APIDatabaseVersions:
        """GET /v1/databases/versions — scope `databases:read`. Catalog keyed by engine `type`:
        `recommended` and `available` lines for new databases. A database's version cannot be
        changed after creation; security updates are applied when it is stopped and started."""
        return self._c.request_json("GET", "/v1/databases/versions")

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

    def metrics(self, db_id: str, *, workspace_id: str | None = None) -> list[APIDatabaseMetrics]:
        """GET /v1/databases/:id/metrics — scope `databases:read`. JSON, not SSE."""
        return self._c.request_json(
            "GET", f"/v1/databases/{encode_path_param(db_id)}/metrics", query={"workspace_id": workspace_id}
        )

    def create(self, body: CreateDatabaseBody) -> APIDatabaseCreated:
        """POST /v1/databases — scope `databases:write`.
        With `snapshot_id` the answer is 202: the database is created first and the data comes back in the
        background: the answer has `restore_job_id` (follow it with `snapshot_jobs.wait(db_id, job_id,
        "databases")`). If the restore fails the database is kept as it is, empty or with what you wrote to it; the
        job's `reason` says why.
        Errors: `INVALID_DATABASE_VERSION`, `SNAPSHOT_VERSION_NEWER`, `SNAPSHOT_EXCEEDS_STORAGE`."""
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

    def reset(
        self,
        db_id: str,
        *,
        workspace_id: str | None = None,
        timeout: float | None = None,
    ) -> APIDatabaseReset:
        """POST /v1/databases/:id/reset — scope `databases:delete`. Resets the database right away and returns
        `{"status": "success"}`. It is permanent: take a snapshot first (`snapshots.create`) if you may need the
        data again."""
        return self._c.request_json(
            "POST",
            f"/v1/databases/{encode_path_param(db_id)}/reset",
            query={"workspace_id": workspace_id},
            timeout=timeout,
        )

    def delete(
        self,
        db_id: str,
        *,
        workspace_id: str | None = None,
        timeout: float | None = None,
    ) -> str:
        """DELETE /v1/databases/:id — scope `databases:delete`. Deletes the database right away and returns its
        id. It is permanent: take a snapshot first (`snapshots.create`) if you may need the data again."""
        return self._c.request_json(
            "DELETE",
            f"/v1/databases/{encode_path_param(db_id)}",
            query={"workspace_id": workspace_id},
            timeout=timeout,
        )
