"""`apps` domain — 42 routes (scopes `apps:read/write/delete/envs/files`).

`workspace_id` is accepted as an optional query parameter on almost every method.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from ..client import LARGE_PAYLOAD_TIMEOUT, MultipartField, encode_path_param
from ..errors import AppBuildFailedError, WaitTimeoutError
from ..sse import SseStream
from ..types import (
    AddDomainBody,
    APIAppFileUploadResponse,
    APIApplication,
    APIApplicationDeployment,
    APIApplicationDomain,
    APIApplicationDomainConnect,
    APIApplicationDomainDnsRecord,
    APIApplicationEnvironment,
    APIApplicationFileContent,
    APIApplicationFileTree,
    APIApplicationOperationResponse,
    APIApplicationRelease,
    APIApplicationReleaseLog,
    APIApplicationReleasePage,
    APIApplicationRollbackPreview,
    APIApplicationStatus,
    APIApplicationStatusShort,
    APIApplicationWebPublish,
    APIRuntimesResponse,
    APISubdomainResponse,
    APIWebhookUrl,
    CreateAppBody,
    CreateWebhookBody,
    EnvironmentSetBody,
    JsonValue,
    MoveFileBody,
    PublishAppBody,
    PurgeCacheBody,
    RestartAppBody,
    RollbackAppBody,
    SetSubdomainBody,
    UpdateAppConfigBody,
    UpdateDomainBody,
)

if TYPE_CHECKING:
    from ..client import VertraClient

# Aliases so `list[...]` doesn't resolve to the `list` method inside the class itself.
EnvList = list[APIApplicationEnvironment]
FileTreeList = list[APIApplicationFileTree]
DomainList = list[APIApplicationDomain]
DomainDnsList = list[APIApplicationDomainDnsRecord]


class AppDeploysWebhookResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def get(self, app_id: str, *, workspace_id: str | None = None) -> APIWebhookUrl:
        """GET /v1/apps/:id/deploys/webhook — scope `apps:read`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/apps/deploys/webhookurl
        """
        return self._c.request_json(
            "GET", f"/v1/apps/{encode_path_param(app_id)}/deploys/webhook", query={"workspace_id": workspace_id}
        )

    def create(self, app_id: str, body: CreateWebhookBody, *, workspace_id: str | None = None) -> APIWebhookUrl:
        """POST /v1/apps/:id/deploys/webhook — scope `apps:write`."""
        return self._c.request_json(
            "POST",
            f"/v1/apps/{encode_path_param(app_id)}/deploys/webhook",
            json_body=body,
            query={"workspace_id": workspace_id},
        )

    def delete(self, app_id: str, *, workspace_id: str | None = None) -> None:
        """DELETE /v1/apps/:id/deploys/webhook (singular) — scope `apps:write`."""
        return self._c.request_json(
            "DELETE", f"/v1/apps/{encode_path_param(app_id)}/deploys/webhook", query={"workspace_id": workspace_id}
        )


class AppDeploysResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client
        self.webhook = AppDeploysWebhookResource(client)

    def list(self, app_id: str, *, workspace_id: str | None = None) -> list[APIApplicationDeployment]:
        """GET /v1/apps/:id/deploys — scope `apps:read`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/apps/deploys/recents
        """
        return self._c.request_json(
            "GET", f"/v1/apps/{encode_path_param(app_id)}/deploys", query={"workspace_id": workspace_id}
        )


class AppReleasesResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(
        self,
        app_id: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        workspace_id: str | None = None,
    ) -> APIApplicationReleasePage:
        """GET /v1/apps/:id/releases — scope `apps:read`. Newest first, paginated; `limit`
        defaults to 20 and the maximum is 50 (larger values fail with `VALIDATION_ERROR`).
        Doc: https://docs.vertracloud.app/api-reference/endpoint/apps/releases/list
        """
        return self._c.request_json(
            "GET",
            f"/v1/apps/{encode_path_param(app_id)}/releases",
            query={"page": page, "limit": limit, "workspace_id": workspace_id},
        )

    def log(self, app_id: str, release_id: str, *, workspace_id: str | None = None) -> APIApplicationReleaseLog:
        """GET /v1/apps/:id/releases/:release_id/log — scope `apps:read`. The crash log of the
        release; `content` is `None` when there is no log or it has expired.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/apps/releases/log
        """
        return self._c.request_json(
            "GET",
            f"/v1/apps/{encode_path_param(app_id)}/releases/{encode_path_param(release_id)}/log",
            query={"workspace_id": workspace_id},
        )

    def preview_rollback(
        self, app_id: str, release_id: str, *, workspace_id: str | None = None
    ) -> APIApplicationRollbackPreview:
        """GET /v1/apps/:id/releases/:release_id/rollback — scope `apps:envs`. Changes nothing.
        Returns `environment_changes`, a list of `{key, change}` (`added`, `modified` or
        `removed`) for what `restore_environment=True` would do. Only variable names are
        returned, never values. Raises a 403 `PLAN_DOES_NOT_SUPPORT_ROLLBACK` when the plan has no rollback.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/apps/releases/rollback-preview
        """
        return self._c.request_json(
            "GET",
            f"/v1/apps/{encode_path_param(app_id)}/releases/{encode_path_param(release_id)}/rollback",
            query={"workspace_id": workspace_id},
        )

    def rollback(
        self,
        app_id: str,
        release_id: str,
        body: RollbackAppBody | None = None,
        *,
        workspace_id: str | None = None,
    ) -> APIApplicationRelease:
        """POST /v1/apps/:id/releases/:release_id/rollback — scope `apps:write`; with
        `restore_environment=True` the key also needs `apps:envs`. Restores the release's code,
        restarts the app and returns the new release (`source == "rollback"`). The current
        environment variables are kept unless `restore_environment` is `True`.
        Errors: `PLAN_DOES_NOT_SUPPORT_ROLLBACK`, `RELEASE_NOT_FOUND`, `RELEASE_ALREADY_ACTIVE`,
        `RELEASE_EXPIRED`, `OPERATION_IN_PROGRESS`, `RESTORE_COOLDOWN`, `DEPLOY_RATE_LIMITED`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/apps/releases/rollback
        """
        return self._c.request_json(
            "POST",
            f"/v1/apps/{encode_path_param(app_id)}/releases/{encode_path_param(release_id)}/rollback",
            json_body=body or {},
            query={"workspace_id": workspace_id},
        )


class AppDomainsResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(self, app_id: str, *, workspace_id: str | None = None) -> DomainList:
        """GET /v1/apps/:id/domains — scope `apps:read`. Automatic companions included."""
        return self._c.request_json(
            "GET", f"/v1/apps/{encode_path_param(app_id)}/domains", query={"workspace_id": workspace_id}
        )

    def add(self, app_id: str, body: AddDomainBody, *, workspace_id: str | None = None) -> DomainList:
        """POST /v1/apps/:id/domains — scope `apps:write`. Returns the created domain and its companion."""
        return self._c.request_json(
            "POST",
            f"/v1/apps/{encode_path_param(app_id)}/domains",
            json_body=body,
            query={"workspace_id": workspace_id},
        )

    def update(
        self, app_id: str, domain_id: str, body: UpdateDomainBody, *, workspace_id: str | None = None
    ) -> DomainList:
        """PATCH /v1/apps/:id/domains/:domain_id — scope `apps:write`."""
        return self._c.request_json(
            "PATCH",
            f"/v1/apps/{encode_path_param(app_id)}/domains/{encode_path_param(domain_id)}",
            json_body=body,
            query={"workspace_id": workspace_id},
        )

    def remove(self, app_id: str, domain_id: str, *, workspace_id: str | None = None) -> None:
        """DELETE /v1/apps/:id/domains/:domain_id — scope `apps:write`. Also removes the automatic companion."""
        return self._c.request_json(
            "DELETE",
            f"/v1/apps/{encode_path_param(app_id)}/domains/{encode_path_param(domain_id)}",
            query={"workspace_id": workspace_id},
        )

    def dns(self, app_id: str, domain_id: str, *, workspace_id: str | None = None) -> DomainDnsList:
        """GET /v1/apps/:id/domains/:domain_id/dns — scope `apps:read`."""
        return self._c.request_json(
            "GET",
            f"/v1/apps/{encode_path_param(app_id)}/domains/{encode_path_param(domain_id)}/dns",
            query={"workspace_id": workspace_id},
        )

    def connect(self, app_id: str, domain_id: str, *, workspace_id: str | None = None) -> APIApplicationDomainConnect:
        """POST /v1/apps/:id/domains/:domain_id/connect — scope `apps:write`. Raises a 404
        `DOMAIN_CONNECT_UNAVAILABLE` when the DNS provider does not support it."""
        return self._c.request_json(
            "POST",
            f"/v1/apps/{encode_path_param(app_id)}/domains/{encode_path_param(domain_id)}/connect",
            query={"workspace_id": workspace_id},
        )


class AppNetworkResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def purge_cache(self, app_id: str, body: PurgeCacheBody | None = None, *, workspace_id: str | None = None) -> None:
        """POST /v1/apps/:id/network/purge-cache — scope `apps:write`. An empty `{}` body is valid."""
        return self._c.request_json(
            "POST",
            f"/v1/apps/{encode_path_param(app_id)}/network/purge-cache",
            json_body=body or {},
            query={"workspace_id": workspace_id},
        )

    def set_subdomain(
        self, app_id: str, body: SetSubdomainBody, *, workspace_id: str | None = None
    ) -> APISubdomainResponse:
        """PATCH /v1/apps/:id/network/subdomain — scope `apps:write`."""
        return self._c.request_json(
            "PATCH",
            f"/v1/apps/{encode_path_param(app_id)}/network/subdomain",
            json_body=body,
            query={"workspace_id": workspace_id},
        )

    def publish(
        self, app_id: str, body: PublishAppBody | None = None, *, workspace_id: str | None = None
    ) -> APIApplicationWebPublish:
        """POST /v1/apps/:id/network/publish — scope `apps:write`. The Pro plan gets a random
        subdomain, Scale picks its own; an empty `{}` body is valid."""
        return self._c.request_json(
            "POST",
            f"/v1/apps/{encode_path_param(app_id)}/network/publish",
            json_body=body or {},
            query={"workspace_id": workspace_id},
        )

    def unpublish(self, app_id: str, *, workspace_id: str | None = None) -> None:
        """DELETE /v1/apps/:id/network/publish — scope `apps:write`."""
        return self._c.request_json(
            "DELETE", f"/v1/apps/{encode_path_param(app_id)}/network/publish", query={"workspace_id": workspace_id}
        )


class AppEnvsResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(self, app_id: str, *, workspace_id: str | None = None) -> EnvList:
        """GET /v1/apps/:id/envs — scope `apps:envs`."""
        return self._c.request_json(
            "GET", f"/v1/apps/{encode_path_param(app_id)}/envs", query={"workspace_id": workspace_id}
        )

    def set(self, app_id: str, body: EnvironmentSetBody, *, workspace_id: str | None = None) -> EnvList:
        """POST /v1/apps/:id/envs — scope `apps:envs`. Body: um objeto `{key,value,note?}` ou
        uma lista deles."""
        return self._c.request_json(
            "POST", f"/v1/apps/{encode_path_param(app_id)}/envs", json_body=body, query={"workspace_id": workspace_id}
        )

    def delete(self, app_id: str, env_id: str, *, workspace_id: str | None = None) -> None:
        """DELETE /v1/apps/:id/envs/:envId — scope `apps:envs`."""
        return self._c.request_json(
            "DELETE",
            f"/v1/apps/{encode_path_param(app_id)}/envs/{encode_path_param(env_id)}",
            query={"workspace_id": workspace_id},
        )


class AppFilesResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(self, app_id: str, *, path: str | None = None, workspace_id: str | None = None) -> JsonValue:
        """GET /v1/apps/:id/files — scope `apps:files`."""
        return self._c.request_json(
            "GET", f"/v1/apps/{encode_path_param(app_id)}/files", query={"path": path, "workspace_id": workspace_id}
        )

    def tree(self, app_id: str, *, path: str | None = None, workspace_id: str | None = None) -> FileTreeList:
        """GET /v1/apps/:id/files/tree — scope `apps:files`."""
        return self._c.request_json(
            "GET",
            f"/v1/apps/{encode_path_param(app_id)}/files/tree",
            query={"path": path, "workspace_id": workspace_id},
        )

    def read(self, app_id: str, *, path: str, workspace_id: str | None = None) -> APIApplicationFileContent:
        """GET /v1/apps/:id/files/content — scope `apps:files`."""
        return self._c.request_json(
            "GET",
            f"/v1/apps/{encode_path_param(app_id)}/files/content",
            query={"path": path, "workspace_id": workspace_id},
        )

    def write(
        self,
        app_id: str,
        *,
        path: str,
        content: str | None = None,
        last_modified: str | None = None,
        workspace_id: str | None = None,
    ) -> None:
        """PUT /v1/apps/:id/files — scope `apps:files`. Response is void."""
        body = {"path": path, "content": content, "last_modified": last_modified, "workspace_id": workspace_id}
        return self._c.request_json(
            "PUT",
            f"/v1/apps/{encode_path_param(app_id)}/files",
            json_body={k: v for k, v in body.items() if v is not None},
        )

    def move(self, app_id: str, body: MoveFileBody, *, workspace_id: str | None = None) -> None:
        """PATCH /v1/apps/:id/files — scope `apps:files`. Body: `{path, to, workspace_id?}`."""
        merged = {**body, "workspace_id": workspace_id or body.get("workspace_id")}
        return self._c.request_json(
            "PATCH",
            f"/v1/apps/{encode_path_param(app_id)}/files",
            json_body={k: v for k, v in merged.items() if v is not None},
        )

    def delete(self, app_id: str, *, path: str, workspace_id: str | None = None) -> None:
        """DELETE /v1/apps/:id/files — scope `apps:files`. Body: `{path, workspace_id?}`."""
        body = {"path": path, "workspace_id": workspace_id}
        return self._c.request_json(
            "DELETE",
            f"/v1/apps/{encode_path_param(app_id)}/files",
            json_body={k: v for k, v in body.items() if v is not None},
        )

    def upload(
        self,
        app_id: str,
        *,
        file: bytes,
        filename: str,
        restart: bool | None = None,
        path: str | None = None,
        message: str | None = None,
        workspace_id: str | None = None,
        timeout: float | None = None,
    ) -> APIAppFileUploadResponse:
        """POST /v1/apps/:id/files/upload — scope `apps:files`. Multipart, field `file`;
        `restart` goes as the query string `"true"`/`"false"`, not a JSON bool.
        `path` is the destination folder inside the app (omitted or empty means the root);
        a ZIP is extracted into it, any other file is written to `path/<filename>`.
        `message` (up to 500 characters) is the commit message shown in the release history.
        Returns `app_id` and `updated_at`; ZIP uploads also include dependency metadata."""
        fields = [MultipartField("file", file, filename=filename)]
        if message is not None:
            fields.append(MultipartField("message", message))
        return self._c.request_multipart(
            "POST",
            f"/v1/apps/{encode_path_param(app_id)}/files/upload",
            fields=fields,
            query={"restart": restart, "path": path, "workspace_id": workspace_id},
            timeout=timeout if timeout is not None else LARGE_PAYLOAD_TIMEOUT,
        )


class AppsResource:
    """`apps.*` — get/status/statusAll/runtimes/realtime/metrics/logs/download/create/start/
    stop/restart/updateConfig/delete + `deploys`, `releases`, `domains`, `network`, `envs`, `files`."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client
        self.deploys = AppDeploysResource(client)
        self.releases = AppReleasesResource(client)
        self.domains = AppDomainsResource(client)
        self.network = AppNetworkResource(client)
        self.envs = AppEnvsResource(client)
        self.files = AppFilesResource(client)

    def get(self, app_id: str, *, workspace_id: str | None = None) -> APIApplication:
        """GET /v1/apps/:id — scope `apps:read`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/apps/get
        """
        return self._c.request_json(
            "GET", f"/v1/apps/{encode_path_param(app_id)}", query={"workspace_id": workspace_id}
        )

    def status(self, app_id: str, *, workspace_id: str | None = None) -> APIApplicationStatus:
        """GET /v1/apps/:id/status — scope `apps:read`."""
        return self._c.request_json(
            "GET", f"/v1/apps/{encode_path_param(app_id)}/status", query={"workspace_id": workspace_id}
        )

    def status_all(self, *, workspace_id: str | None = None) -> list[APIApplicationStatusShort]:
        """GET /v1/apps/status — scope `apps:read`."""
        return self._c.request_json("GET", "/v1/apps/status", query={"workspace_id": workspace_id})

    def runtimes(self) -> APIRuntimesResponse:
        """GET /v1/apps/runtimes — scope `apps:read`."""
        return self._c.request_json("GET", "/v1/apps/runtimes")

    def metrics(
        self, app_id: str, *, workspace_id: str | None = None, range: str | None = None, since: int | None = None
    ) -> list[Any]:
        """GET /v1/apps/:id/metrics — scope `apps:read`. Rate limit 50/min. JSON, not SSE."""
        return self._c.request_json(
            "GET",
            f"/v1/apps/{encode_path_param(app_id)}/metrics",
            query={"workspace_id": workspace_id, "range": range, "since": since},
        )

    def logs(self, app_id: str, *, workspace_id: str | None = None) -> str:
        """GET /v1/apps/:id/logs — scope `apps:read`. Rate limit 60/min. Returns a string, not an object."""
        return self._c.request_json(
            "GET", f"/v1/apps/{encode_path_param(app_id)}/logs", query={"workspace_id": workspace_id}
        )

    def download(self, app_id: str, *, workspace_id: str | None = None, timeout: float | None = None) -> bytes:
        """GET /v1/apps/:id/download — scope `apps:read`. Binary zip. Rate limit 10/min."""
        return self._c.request_binary(
            "GET",
            f"/v1/apps/{encode_path_param(app_id)}/download",
            query={"workspace_id": workspace_id},
            timeout=timeout if timeout is not None else LARGE_PAYLOAD_TIMEOUT,
        )

    def realtime(
        self, app_id: str, *, since: int | None = None, workspace_id: str | None = None, timeout: float | None = None
    ) -> SseStream:
        """GET /v1/apps/:id/realtime — scope `apps:read`. The only SSE route in the catalog. No
        automatic reconnection — the stream closes when the connection ends or via `.close()`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/apps/realtime
        """
        return self._c.request_sse(
            f"/v1/apps/{encode_path_param(app_id)}/realtime",
            query={"since": since, "workspace_id": workspace_id},
            timeout=timeout,
        )

    def create(
        self,
        body: CreateAppBody | None = None,
        *,
        file: bytes | None = None,
        filename: str = "app.zip",
        timeout: float | None = None,
    ) -> APIApplication:
        """POST /v1/apps — scope `apps:write`. Multipart: field `file` (zip) OR `snapshot_id`
        in `body`, other fields as text parts. Rate limit 15/min, plus the plan's
        deploys-per-hour cap. Replies 202 with `status: "building"`: the build continues in the
        background — use `wait_until_ready`, `logs` or `realtime` to follow it.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/apps/create
        """
        fields: list[MultipartField] = []
        data = dict(body or {})
        if file is not None:
            fields.append(MultipartField("file", file, filename=filename))
        envs = data.pop("envs", None)
        if envs is not None:
            import json as _json

            fields.append(MultipartField("envs", _json.dumps(envs)))
        for key, value in data.items():
            if value is None:
                continue
            text = "true" if value is True else "false" if value is False else str(value)
            fields.append(MultipartField(key, text))
        return self._c.request_multipart(
            "POST", "/v1/apps", fields=fields, timeout=timeout if timeout is not None else LARGE_PAYLOAD_TIMEOUT
        )

    def wait_until_ready(
        self,
        app_id: str,
        *,
        timeout: float = 600.0,
        interval: float = 2.0,
        workspace_id: str | None = None,
    ) -> APIApplication:
        """Polls `GET /v1/apps/:id` while `status` is `building`. Returns the app when it is `up`;
        raises `AppBuildFailedError` when it ends `down` and `WaitTimeoutError` after `timeout`
        seconds. API errors from the polling propagate unchanged."""
        deadline = time.monotonic() + timeout
        while True:
            app = self.get(app_id, workspace_id=workspace_id)
            if app["status"] == "up":
                return app
            if app["status"] == "down":
                raise AppBuildFailedError(
                    "the build ended and the app is down; read apps.logs for the cause",
                    code=app.get("last_build_error") or "APP_DOWN",
                    app=app,
                )
            if time.monotonic() + interval > deadline:
                raise WaitTimeoutError(f"still building after {timeout:g}s", code="WAIT_TIMEOUT", app=app)
            time.sleep(interval)

    def start(self, app_id: str, *, workspace_id: str | None = None) -> APIApplicationOperationResponse:
        """POST /v1/apps/:id/start — scope `apps:write`."""
        return self._c.request_json(
            "POST", f"/v1/apps/{encode_path_param(app_id)}/start", query={"workspace_id": workspace_id}
        )

    def stop(self, app_id: str, *, workspace_id: str | None = None) -> APIApplicationOperationResponse:
        """POST /v1/apps/:id/stop — scope `apps:write`."""
        return self._c.request_json(
            "POST", f"/v1/apps/{encode_path_param(app_id)}/stop", query={"workspace_id": workspace_id}
        )

    def restart(
        self, app_id: str, body: RestartAppBody | None = None, *, workspace_id: str | None = None
    ) -> APIApplicationOperationResponse:
        """POST /v1/apps/:id/restart — scope `apps:write`. Flags: `reinstall_dependencies`,
        `force_build`, `cleanup_old_runtime_language`."""
        return self._c.request_json(
            "POST",
            f"/v1/apps/{encode_path_param(app_id)}/restart",
            json_body=body or {},
            query={"workspace_id": workspace_id},
        )

    def update_config(self, app_id: str, body: UpdateAppConfigBody, *, workspace_id: str | None = None) -> str:
        """PATCH /v1/apps/:id/config — scope `apps:write`. Returns `"success"`, not the app.
        `deploy` sets `zero_downtime` (`"auto"`, `"on"`, `"off"`), `auto_rollback` and
        `health_check_path`; omit a key to leave it unchanged, pass `None` as the path to clear it.
        `zero_downtime="on"` and `auto_rollback=True` need a higher plan and fail with
        `PLAN_DOES_NOT_SUPPORT_ZERO_DOWNTIME` / `PLAN_DOES_NOT_SUPPORT_AUTO_ROLLBACK`."""
        return self._c.request_json(
            "PATCH",
            f"/v1/apps/{encode_path_param(app_id)}/config",
            json_body=body,
            query={"workspace_id": workspace_id},
        )

    def delete(self, app_id: str, *, workspace_id: str | None = None) -> None:
        """DELETE /v1/apps/:id — scope `apps:delete`."""
        return self._c.request_json(
            "DELETE", f"/v1/apps/{encode_path_param(app_id)}", query={"workspace_id": workspace_id}
        )
