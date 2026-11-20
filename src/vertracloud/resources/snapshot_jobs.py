"""`snapshot_jobs` domain — 2 routes, under `/v1/users/:id/snapshots/jobs` (scope `snapshots:read`).

A snapshot or a restore runs as a job. `:id` is the resource the job acts on (the app or database being backed up or
restored). `scope` (`"applications"` or `"databases"`) is required to list and optional to get one job by its id.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from ..client import DEFAULT_WAIT_TIMEOUT, encode_path_param
from ..errors import SnapshotJobFailedError, SnapshotJobSkippedError, SnapshotJobTimeoutError
from ..types import APISnapshotJob, SnapshotJobKind, SnapshotScope

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..client import VertraClient


class SnapshotJobsResource:
    """`snapshot_jobs.*` — list/get, plus `wait` to follow one job until it ends."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(
        self,
        resource_id: str,
        scope: SnapshotScope,
        *,
        kind: SnapshotJobKind | None = None,
        limit: int | None = None,
        workspace_id: str | None = None,
        timeout: float | None = None,
    ) -> list[APISnapshotJob]:
        """GET /v1/users/:id/snapshots/jobs — scope `snapshots:read`. Jobs of one resource, most recent first.
        `kind` keeps one kind (default: both); `limit` is 1 to 50 (default 10; outside that the API answers 400
        `VALIDATION_ERROR`). `timeout` is per request."""
        return self._c.request_json(
            "GET",
            f"/v1/users/{encode_path_param(resource_id)}/snapshots/jobs",
            query={"scope": scope, "kind": kind, "limit": limit, "workspace_id": workspace_id},
            timeout=timeout,
        )

    def get(
        self,
        resource_id: str,
        job_id: str,
        scope: SnapshotScope | None = None,
        *,
        workspace_id: str | None = None,
        timeout: float | None = None,
    ) -> APISnapshotJob:
        """GET /v1/users/:id/snapshots/jobs/:job_id — scope `snapshots:read`. `scope` is optional here: the job is
        found by its id. A job of another resource, another account or one that does not exist is
        404 `SNAPSHOT_NOT_FOUND`. `status` is `queued`, `running`, `ready`, `skipped` or `failed` (`reason` says
        why). `timeout` is per request."""
        return self._c.request_json(
            "GET",
            f"/v1/users/{encode_path_param(resource_id)}/snapshots/jobs/{encode_path_param(job_id)}",
            query={"scope": scope, "workspace_id": workspace_id},
            timeout=timeout,
        )

    def wait(
        self,
        resource_id: str,
        job_id: str,
        scope: SnapshotScope | None = None,
        *,
        workspace_id: str | None = None,
        timeout: float | None = None,
        wait_timeout: float = DEFAULT_WAIT_TIMEOUT,
        interval: float = 2.0,
        on_progress: Callable[[APISnapshotJob], None] | None = None,
    ) -> APISnapshotJob:
        """Polls `get` every `interval` seconds until the job ends, for at most `wait_timeout` seconds in total (30
        minutes by default); `timeout` is the limit of each request. Returns the job when it ends `ready`; raises
        `SnapshotJobFailedError` or `SnapshotJobSkippedError` (`code` and `reason` = the job's `reason`, `details`,
        `job`) when it ends `failed` or `skipped`, and `SnapshotJobTimeoutError` (with the last `job`) when the time
        runs out; the job keeps running. API errors from the polling propagate unchanged. `on_progress` is called
        with the job on every poll while it has not ended: `job["status"]`, and `job["progress"]` while it is
        `running`."""
        deadline = time.monotonic() + wait_timeout
        while True:
            job = self.get(resource_id, job_id, scope, workspace_id=workspace_id, timeout=timeout)
            status = job.get("status")
            if status == "ready":
                return job
            if status == "failed":
                raise SnapshotJobFailedError(
                    f"the {job['kind']} job ended failed", code=job.get("reason") or "SNAPSHOT_FAILED", job=job
                )
            if status == "skipped":
                raise SnapshotJobSkippedError(
                    f"the {job['kind']} job ended skipped", code=job.get("reason") or "SNAPSHOT_FAILED", job=job
                )
            if on_progress is not None:
                on_progress(job)
            if time.monotonic() + interval > deadline:
                raise SnapshotJobTimeoutError(
                    f"job still {status} after {wait_timeout:g}s", code="WAIT_TIMEOUT", job=job
                )
            time.sleep(interval)
