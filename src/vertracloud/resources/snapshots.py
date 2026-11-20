"""`snapshots` domain — 5 routes, under `/v1/users/:id/snapshots` (scopes `snapshots:read/write`).
The jobs they start are followed with `client.snapshot_jobs`.

`scope` (`"applications"` or `"databases"`) is a **required** query parameter on all 5 routes —
without it the API responds 400 `INVALID_QUERY`.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, cast

from ..client import DEFAULT_WAIT_TIMEOUT, encode_path_param
from ..errors import NotFoundError
from ..types import (
    APIGroupedResourceSnapshots,
    APIResourceSnapshot,
    APISnapshotCreateAccepted,
    APISnapshotJob,
    APISnapshotRestoreAccepted,
    SnapshotScope,
)
from .snapshot_jobs import SnapshotJobsResource

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from ..client import VertraClient


class SnapshotsResource:
    """`snapshots.*` — list_all/list/download/download_stream/download_to_file/create/create_and_wait/restore."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list_all(self, scope: SnapshotScope) -> list[APIGroupedResourceSnapshots]:
        """GET /v1/users/snapshots — scope `snapshots:read`."""
        return self._c.request_json("GET", "/v1/users/snapshots", query={"scope": scope})

    def list(
        self, resource_id: str, scope: SnapshotScope, *, workspace_id: str | None = None, timeout: float | None = None
    ) -> list[APIResourceSnapshot]:
        """GET /v1/users/:id/snapshots — scope `snapshots:read`. `:id` is the app/database, not the user.
        `workspace_id`: the workspace the resource belongs to (every `snapshots.*` call below takes it too)."""
        return self._c.request_json(
            "GET",
            f"/v1/users/{encode_path_param(resource_id)}/snapshots",
            query={"scope": scope, "workspace_id": workspace_id},
            timeout=timeout,
        )

    def download(
        self,
        resource_id: str,
        snapshot_id: str,
        scope: SnapshotScope,
        *,
        workspace_id: str | None = None,
        timeout: float | None = None,
    ) -> bytes:
        """GET /v1/users/:id/snapshots/:snapshot_id/download — scope `snapshots:read`. Zip file. There is no total
        deadline: `timeout` (default the client's) is the wait of each socket operation, so a large file that keeps
        arriving completes and one that stalls fails once `timeout` passes without bytes.

        The whole file is held in memory: for a snapshot that can be large use `download_to_file` (writes to disk as
        the bytes arrive) or `download_stream`."""
        return self._c.request_binary(
            "GET",
            self._download_path(resource_id, snapshot_id),
            query={"scope": scope, "workspace_id": workspace_id},
            timeout=timeout,
        )

    def download_stream(
        self,
        resource_id: str,
        snapshot_id: str,
        scope: SnapshotScope,
        *,
        workspace_id: str | None = None,
        timeout: float | None = None,
    ) -> Iterator[bytes]:
        """Same download as `download`, as an iterator of byte chunks (1 MiB at most) read as you ask for them: memory
        does not grow with the file. Same `timeout` (the wait of each read). Iterate to the end or call `close()` on
        the iterator to release the connection."""
        return self._c.request_binary_stream(
            "GET",
            self._download_path(resource_id, snapshot_id),
            query={"scope": scope, "workspace_id": workspace_id},
            timeout=timeout,
        )

    def download_to_file(
        self,
        resource_id: str,
        snapshot_id: str,
        scope: SnapshotScope,
        path: str | os.PathLike[str],
        *,
        workspace_id: str | None = None,
        timeout: float | None = None,
    ) -> int:
        """Same download as `download`, written to `path` as the bytes arrive: memory stays constant whatever the size
        (a snapshot of 8 GB is fine). The bytes go to a temporary file next to `path`, renamed to it only when the
        download ends; on failure, stall (`timeout` without bytes) or `KeyboardInterrupt` the temporary file is
        removed and `path` never holds a partial file. An existing `path` is replaced at the end. Returns the number
        of bytes written."""
        return self._c.download_to_file(
            "GET",
            self._download_path(resource_id, snapshot_id),
            path,
            query={"scope": scope, "workspace_id": workspace_id},
            timeout=timeout,
        )

    @staticmethod
    def _download_path(resource_id: str, snapshot_id: str) -> str:
        return f"/v1/users/{encode_path_param(resource_id)}/snapshots/{encode_path_param(snapshot_id)}/download"

    def create(
        self, resource_id: str, scope: SnapshotScope, *, workspace_id: str | None = None, timeout: float | None = None
    ) -> APIResourceSnapshot | APISnapshotCreateAccepted:
        """POST /v1/users/:id/snapshots — scope `snapshots:write`. Can take about 90 s: `timeout` defaults to
        120 s (or the client's, if larger). Limits: a daily quota per account, plus a wait between snapshots of the
        same resource; over them the call fails with `SNAPSHOT_RATE_LIMITED` (429), whose `RateLimitError.retry_after`
        and `details` (`scope`, `resets_at`) say when to try again. One request: a snapshot still being taken after
        about 90 s answers 202 and the call returns `{"job_id": ...}` instead of a snapshot (check for the `job_id`
        key): follow the job with `snapshot_jobs.wait` (a `ready` job has the `snapshot_id`), or use
        `create_and_wait` to do both."""
        return self._c.request_json(
            "POST",
            f"/v1/users/{encode_path_param(resource_id)}/snapshots",
            json_body={},
            query={"scope": scope, "workspace_id": workspace_id},
            timeout=self._c.snapshot_action_timeout(timeout),
        )

    def create_and_wait(
        self,
        resource_id: str,
        scope: SnapshotScope,
        *,
        workspace_id: str | None = None,
        timeout: float | None = None,
        wait_timeout: float = DEFAULT_WAIT_TIMEOUT,
        interval: float = 2.0,
        on_progress: Callable[[APISnapshotJob], None] | None = None,
    ) -> APIResourceSnapshot:
        """`create` and, when the API answers 202, `snapshot_jobs.wait` for the job (every `interval` seconds, up to
        `wait_timeout`, 30 minutes by default). Returns the snapshot. Raises `SnapshotJobFailedError` or
        `SnapshotJobSkippedError` (`code`/`reason`, `details`, `job`) when the job ends that way and
        `SnapshotJobTimeoutError` when the wait runs out (the snapshot keeps being taken). `timeout` is the limit of
        each request and `wait_timeout` the total wait; `on_progress` is called with the job on every poll while it
        has not ended."""
        created = self.create(resource_id, scope, workspace_id=workspace_id, timeout=timeout)
        if "job_id" not in created:
            return created
        job_id = cast("APISnapshotCreateAccepted", created)["job_id"]
        job = SnapshotJobsResource(self._c).wait(
            resource_id,
            job_id,
            scope,
            workspace_id=workspace_id,
            timeout=timeout,
            wait_timeout=wait_timeout,
            interval=interval,
            on_progress=on_progress,
        )
        for snapshot in self.list(resource_id, scope, workspace_id=workspace_id, timeout=timeout):
            if snapshot["id"] == job.get("snapshot_id"):
                return snapshot
        raise NotFoundError(
            f"snapshot job {job_id} is ready but its snapshot is not in the list", status=404, code="SNAPSHOT_NOT_FOUND"
        )

    def restore(
        self,
        resource_id: str,
        snapshot_id: str,
        scope: SnapshotScope,
        *,
        restore_image_version: bool | None = None,
        workspace_id: str | None = None,
        timeout: float | None = None,
    ) -> APISnapshotRestoreAccepted:
        """POST /v1/users/:id/snapshots/:snapshot_id/restore — scope `snapshots:write`. The restore runs as a job
        (HTTP 202): the call returns `{"job_id": ..., "warning"?: ...}` and the resource is not restored yet; follow
        `job_id` with `snapshot_jobs.wait(resource_id, job_id, scope)`. While it runs, every write to the resource
        fails with `RESTORE_IN_PROGRESS` (409); reads and deleting it still work.
        Refused up front with `SNAPSHOT_EXCEEDS_STORAGE` (400; `err.snapshot_exceeds_storage`), `APP_BUILDING`
        (409), `RESTORE_IN_PROGRESS` or `RESTORE_COOLDOWN` (429). For database snapshots it can fail with
        `SNAPSHOT_VERSION_NEWER`.
        `restore_image_version` applies to an app on a custom image: `True` also goes back to the image
        version the app ran when the snapshot was taken, if it still exists (the answer then carries
        `warning` when it does not). Omitted, the API restores only the data.

        The restore replaces the current data right away and is permanent for it: take a snapshot first
        (`create`) if you may need it again. The wait between restores is a 429 `RESTORE_COOLDOWN`."""
        body: dict[str, bool] = {}
        if restore_image_version is not None:
            body["restore_image_version"] = restore_image_version
        return self._c.request_json(
            "POST",
            f"/v1/users/{encode_path_param(resource_id)}/snapshots/{encode_path_param(snapshot_id)}/restore",
            json_body=body,
            query={"scope": scope, "workspace_id": workspace_id},
            timeout=timeout,
        )
