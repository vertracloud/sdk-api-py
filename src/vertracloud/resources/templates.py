"""`templates` domain — the catalog, using a template (deploy), private templates, share links and updating
what was created from a template (scopes `templates:read`, `templates:write` and `templates:deploy`).

A template describes what to create: one application, or a stack with applications, databases and a Blob
folder. `deploy` replies with a job right away; follow it with `deploys.events` (Server-Sent Events) or read
`deploys.get`. A job that fails is undone as a whole. The public catalog (`list`, `get`, `categories`,
`versions`) also answers without a valid key on the API side, but this client always sends the key.

`workspace_id` is a keyword-only query parameter on the routes that act on an existing template, app or stack,
and on `list`; the routes that create something take it in the body. Without it the call acts on the caller's
own resources. Using a template in a workspace, and creating or changing templates of one, is for the owner of
the workspace (`WORKSPACE_OWNER_ONLY` otherwise).
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING, Any

from ..client import LARGE_PAYLOAD_TIMEOUT, MultipartField, encode_path_param
from ..sse import SseStream
from ..types import (
    APIApplication,
    APIStack,
    APITemplateCategoryCount,
    APITemplateDeploy,
    APITemplateDeployEvent,
    APITemplateDetail,
    APITemplateDraft,
    APITemplateManifest,
    APITemplatePage,
    APITemplateShareLink,
    APITemplateShareLinkCreated,
    APITemplateSharePreview,
    APITemplateUpdateInfo,
    APITemplateValidation,
    APITemplateVersion,
    TemplateCategory,
    TemplateCreateBody,
    TemplateDeployBody,
    TemplateFromAppBody,
    TemplateFromStackBody,
    TemplateGithubLinkBody,
    TemplateListSort,
    TemplateOrigin,
    TemplateReportBody,
    TemplateShareCopyBody,
    TemplateShareDeployBody,
    TemplateShareLinkCreateBody,
    TemplateUpdateBody,
    TemplateUpdateDetailsBody,
    TemplateVersionBody,
)

if TYPE_CHECKING:
    from ..client import VertraClient

# Aliases so `list[...]` doesn't resolve to the `list` method inside the class itself.
CategoryCountList = list[APITemplateCategoryCount]
TemplateVersionList = list[APITemplateVersion]
ShareLinkList = list[APITemplateShareLink]


def _template_path(template_id: str, suffix: str = "") -> str:
    return f"/v1/templates/{encode_path_param(template_id)}{suffix}"


def _share_path(token: str, suffix: str = "") -> str:
    return f"/v1/share/templates/{encode_path_param(token)}{suffix}"


class TemplateDeployEventStream:
    """Progress of a deploy job, as decoded events. Iterate it for one `APITemplateDeployEvent` per `progress`
    event: heartbeats are skipped and the iteration ends when the API closes the stream with its `end` event
    (then `ended` is `True`), when the connection ends, or after `close()`. Outputs are never on the stream:
    read them with `templates.deploys.get` once the job is finished."""

    def __init__(self, stream: SseStream) -> None:
        self._stream = stream
        self.ended = False

    def __iter__(self) -> Iterator[APITemplateDeployEvent]:
        for event in self._stream:
            if event.event == "end":
                self.ended = True
                self._stream.close()
                return
            if event.event not in ("progress", "message", ""):
                continue  # heartbeat and unknown events
            if not event.data:
                continue
            try:
                decoded: APITemplateDeployEvent = json.loads(event.data)
            except json.JSONDecodeError as exc:
                raise ValueError("vertracloud: could not decode a deploy event") from exc
            yield decoded

    def close(self) -> None:
        self._stream.close()


class TemplateDeploysResource:
    """`templates.deploys.*` — get/events."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def get(self, deploy_id: str) -> APITemplateDeploy:
        """GET /v1/template-deploys/:deploy_id — scope `templates:deploy`. The job with its steps, the resources
        created and the outputs. Outputs marked `once` come back on the first read of a finished job and are
        empty afterwards.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/deploy-status
        """
        return self._c.request_json("GET", f"/v1/template-deploys/{encode_path_param(deploy_id)}")

    def events(self, deploy_id: str, *, timeout: float | None = None) -> TemplateDeployEventStream:
        """GET /v1/template-deploys/:deploy_id/events — scope `templates:deploy`. A Server-Sent Events stream of
        the progress of the job: it repeats the current state and follows it until the job ends. Iterate it for
        events; `close()` or `break` ends it.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/deploy-events
        """
        stream = self._c.request_sse(f"/v1/template-deploys/{encode_path_param(deploy_id)}/events", timeout=timeout)
        return TemplateDeployEventStream(stream)


class TemplateShareLinksResource:
    """`templates.share_links.*` — create/list/revoke the links of a private template."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def create(
        self,
        template_id: str,
        body: TemplateShareLinkCreateBody | None = None,
        *,
        workspace_id: str | None = None,
    ) -> APITemplateShareLinkCreated:
        """POST /v1/templates/:template_id/share-links — scope `templates:write`. `mode` is `use` (default; the
        link deploys the template) or `full_copy` (the link copies the whole template). The `token` is only in
        this answer.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/share-links/create
        """
        return self._c.request_json(
            "POST",
            _template_path(template_id, "/share-links"),
            json_body=body if body is not None else {},
            query={"workspace_id": workspace_id},
        )

    def list(self, template_id: str, *, workspace_id: str | None = None) -> ShareLinkList:
        """GET /v1/templates/:template_id/share-links — scope `templates:read`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/share-links/list
        """
        return self._c.request_json(
            "GET", _template_path(template_id, "/share-links"), query={"workspace_id": workspace_id}
        )

    def revoke(self, template_id: str, link_id: str, *, workspace_id: str | None = None) -> APITemplateShareLink:
        """DELETE /v1/templates/:template_id/share-links/:link_id — scope `templates:write`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/share-links/revoke
        """
        return self._c.request_json(
            "DELETE",
            _template_path(template_id, f"/share-links/{encode_path_param(link_id)}"),
            query={"workspace_id": workspace_id},
        )


class TemplateShareResource:
    """`templates.share.*` — what a share link gives: preview, use (deploy), copy and report. The `token` comes
    from the link the owner shared."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def preview(self, token: str) -> APITemplateSharePreview:
        """GET /v1/share/templates/:token — scope `templates:read`. What the link offers, without creating anything.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/share-links/preview
        """
        return self._c.request_json("GET", _share_path(token))

    def deploy(
        self, token: str, body: TemplateShareDeployBody, *, idempotency_key: str | None = None
    ) -> APITemplateDeploy:
        """POST /v1/share/templates/:token/deploy — scope `templates:deploy`. Same as `templates.deploy`, without
        a choice of version. `idempotency_key` is sent as the `Idempotency-Key` header, never in the body.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/share-links/deploy
        """
        return self._c.request_json(
            "POST",
            _share_path(token, "/deploy"),
            json_body=_without_key(body),
            extra_headers=_idempotency_headers(idempotency_key),
        )

    def copy(self, token: str, body: TemplateShareCopyBody | None = None) -> APITemplateDetail:
        """POST /v1/share/templates/:token/copy — scope `templates:write`. Only a `full_copy` link: copies the
        template into your account (or into `body["workspace_id"]`).
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/share-links/copy
        """
        return self._c.request_json("POST", _share_path(token, "/copy"), json_body=body if body is not None else {})

    def report(self, token: str, body: TemplateReportBody) -> None:
        """POST /v1/share/templates/:token/report — scope `templates:write`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/share-links/report
        """
        self._c.request_json("POST", _share_path(token, "/report"), json_body=body)


class TemplateUpdatesResource:
    """`templates.updates.*` — read and run the update of an app or a stack that came from a template, and detach it."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def app_info(self, app_id: str, *, workspace_id: str | None = None) -> APITemplateUpdateInfo:
        """GET /v1/apps/:id/template/update — scope `templates:read`. Whether a newer version exists, what it
        changes and why it may be blocked (`blocked`).
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/update-info
        """
        return self._c.request_json(
            "GET", f"/v1/apps/{encode_path_param(app_id)}/template/update", query={"workspace_id": workspace_id}
        )

    def app_update(
        self, app_id: str, body: TemplateUpdateBody | None = None, *, workspace_id: str | None = None
    ) -> APITemplateDeploy:
        """POST /v1/apps/:id/template/update — scope `templates:deploy`. Returns a deploy job (`kind: "update"`);
        follow it as any other. A blocked update fails with `TEMPLATE_UPDATE_BLOCKED` (`VertraAPIError.update_blocked`).
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/update-info
        """
        return self._c.request_json(
            "POST",
            f"/v1/apps/{encode_path_param(app_id)}/template/update",
            json_body=body if body is not None else {},
            query={"workspace_id": workspace_id},
        )

    def app_detach(self, app_id: str, *, workspace_id: str | None = None) -> APIApplication:
        """POST /v1/apps/:id/template/detach — scope `apps:write`. The app stops following its template.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/detach
        """
        return self._c.request_json(
            "POST", f"/v1/apps/{encode_path_param(app_id)}/template/detach", query={"workspace_id": workspace_id}
        )

    def stack_info(self, stack_id: str, *, workspace_id: str | None = None) -> APITemplateUpdateInfo:
        """GET /v1/stacks/:stack_id/template/update — scope `templates:read`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/update-info
        """
        return self._c.request_json(
            "GET", f"/v1/stacks/{encode_path_param(stack_id)}/template/update", query={"workspace_id": workspace_id}
        )

    def stack_update(
        self, stack_id: str, body: TemplateUpdateBody | None = None, *, workspace_id: str | None = None
    ) -> APITemplateDeploy:
        """POST /v1/stacks/:stack_id/template/update — scope `templates:deploy`. Returns a deploy job.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/update-info
        """
        return self._c.request_json(
            "POST",
            f"/v1/stacks/{encode_path_param(stack_id)}/template/update",
            json_body=body if body is not None else {},
            query={"workspace_id": workspace_id},
        )

    def stack_detach(self, stack_id: str, *, workspace_id: str | None = None) -> APIStack:
        """POST /v1/stacks/:stack_id/template/detach — scope `stacks:write`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/detach
        """
        return self._c.request_json(
            "POST", f"/v1/stacks/{encode_path_param(stack_id)}/template/detach", query={"workspace_id": workspace_id}
        )


def _idempotency_headers(key: str | None) -> dict[str, str] | None:
    return {"Idempotency-Key": key} if key else None


def _without_key(body: Mapping[str, Any]) -> dict[str, Any]:
    """The key travels as a header only: a stray `idempotency_key` in the body is dropped."""
    return {k: v for k, v in body.items() if k != "idempotency_key"}


def _template_fields(
    manifest: APITemplateManifest | Mapping[str, Any] | str,
    changelog: Mapping[str, Any] | None,
    workspace_id: str | None,
    sources: Mapping[str, bytes] | None,
) -> list[MultipartField]:
    if manifest is None:
        raise ValueError("manifest is required")
    raw_manifest = manifest if isinstance(manifest, str) else json.dumps(manifest)
    fields = [MultipartField("manifest", raw_manifest)]
    if changelog is not None:
        fields.append(MultipartField("changelog", json.dumps(changelog)))
    if workspace_id is not None:
        fields.append(MultipartField("workspace_id", workspace_id))
    for service_id in sorted(sources or {}):
        fields.append(
            MultipartField(
                f"sources[{service_id}]",
                (sources or {})[service_id],
                filename=f"{service_id}.zip",
                content_type="application/zip",
            )
        )
    return fields


class TemplatesResource:
    """`templates.*` — list/get/categories/versions/validate/deploy, the private templates
    (create/new_version/from_app/from_stack/app_draft/stack_draft/update/delete/link_github/unlink_github/report_app)
    and the sub-resources `deploys`, `share_links`, `share` and `updates`."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client
        self.deploys = TemplateDeploysResource(client)
        self.share_links = TemplateShareLinksResource(client)
        self.share = TemplateShareResource(client)
        self.updates = TemplateUpdatesResource(client)

    # -- catalog -------------------------------------------------------

    def list(
        self,
        *,
        search: str | None = None,
        category: TemplateCategory | None = None,
        origin: TemplateOrigin | None = None,
        tag: str | None = None,
        fits: bool | None = None,
        sort: TemplateListSort | None = None,
        page: int | None = None,
        limit: int | None = None,
        workspace_id: str | None = None,
    ) -> APITemplatePage:
        """GET /v1/templates — scope `templates:read`. The public catalog; `origin="private"` lists your private
        templates (and the ones of `workspace_id`). `fits=True` keeps only the templates that fit your account
        right now. `sort` defaults to `recommended`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/list
        """
        return self._c.request_json(
            "GET",
            "/v1/templates",
            query={
                "search": search,
                "category": category,
                "origin": origin,
                "tag": tag,
                "fits": fits,
                "sort": sort,
                "page": page,
                "limit": limit,
                "workspace_id": workspace_id,
            },
        )

    def get(self, template: str, *, workspace_id: str | None = None) -> APITemplateDetail:
        """GET /v1/templates/:template_id — scope `templates:read`. `template` is the id or the slug.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/get
        """
        return self._c.request_json("GET", _template_path(template), query={"workspace_id": workspace_id})

    def categories(self) -> CategoryCountList:
        """GET /v1/templates/categories — scope `templates:read`. The public catalog, with the number of templates
        per category.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/categories
        """
        return self._c.request_json("GET", "/v1/templates/categories")

    def versions(self, template: str, *, workspace_id: str | None = None) -> TemplateVersionList:
        """GET /v1/templates/:template_id/versions — scope `templates:read`. Newest first.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/versions
        """
        return self._c.request_json("GET", _template_path(template, "/versions"), query={"workspace_id": workspace_id})

    def validate(self, manifest: APITemplateManifest | Mapping[str, Any] | str) -> APITemplateValidation:
        """POST /v1/templates/validate — scope `templates:read`. Checks a manifest (an object, or the YAML/JSON text)
        and creates nothing; the findings are in `issues`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/validate
        """
        return self._c.request_json("POST", "/v1/templates/validate", json_body={"manifest": manifest})

    def deploy(
        self, template: str, body: TemplateDeployBody, *, idempotency_key: str | None = None
    ) -> APITemplateDeploy:
        """POST /v1/templates/:template_id/deploy — scope `templates:deploy`. Creates, as one operation, everything
        the template describes, and replies with a job (`APITemplateDeploy`) right away: follow it with
        `deploys.events` or `deploys.get`. `idempotency_key` is sent as the `Idempotency-Key` header, never in the
        body: repeating the call with the same key and request returns the same job; the same key with another
        request fails with `IDEMPOTENCY_KEY_CONFLICT`. Recommended on every call.
        Errors: `TEMPLATE_PLAN_REQUIRED`, `TEMPLATE_RAM_INSUFFICIENT`, `TEMPLATE_IMAGE_SLOTS_EXHAUSTED`,
        `TEMPLATE_INPUT_INVALID`, `TEMPLATE_DEPLOY_IN_PROGRESS`, `MAX_APPS_REACHED`, `MAX_DATABASES_REACHED`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/deploy
        """
        return self._c.request_json(
            "POST",
            _template_path(template, "/deploy"),
            json_body=_without_key(body),
            extra_headers=_idempotency_headers(idempotency_key),
        )

    # -- private templates ---------------------------------------------

    def create(
        self,
        body: TemplateCreateBody,
        *,
        sources: Mapping[str, bytes] | None = None,
        timeout: float | None = None,
    ) -> APITemplateDetail:
        """POST /v1/templates — scope `templates:write`. Multipart. `body["manifest"]` is the manifest; `sources`
        holds the ZIP of the code of each service of type `code`, by service id (a service of type `image` needs
        none). Creates the template with its first version. A manifest that fails validation raises
        `TEMPLATE_MANIFEST_INVALID` (`VertraAPIError.manifest_issues`); a source with a secret,
        `TEMPLATE_SECRET_IN_SOURCE` (`VertraAPIError.secret_files`).
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/create
        """
        fields = _template_fields(body["manifest"], body.get("changelog"), body.get("workspace_id"), sources)
        return self._c.request_multipart(
            "POST",
            "/v1/templates",
            fields=fields,
            timeout=timeout if timeout is not None else LARGE_PAYLOAD_TIMEOUT,
        )

    def new_version(
        self,
        template_id: str,
        body: TemplateVersionBody,
        *,
        sources: Mapping[str, bytes] | None = None,
        workspace_id: str | None = None,
        timeout: float | None = None,
    ) -> APITemplateVersion:
        """POST /v1/templates/:template_id/versions — scope `templates:write`. Multipart, like `create`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/new-version
        """
        fields = _template_fields(body["manifest"], body.get("changelog"), None, sources)
        return self._c.request_multipart(
            "POST",
            _template_path(template_id, "/versions"),
            fields=fields,
            query={"workspace_id": workspace_id},
            timeout=timeout if timeout is not None else LARGE_PAYLOAD_TIMEOUT,
        )

    def app_draft(self, app_id: str, *, workspace_id: str | None = None) -> APITemplateDraft:
        """GET /v1/templates/from-app/:app_id/draft — scope `templates:write`. The variables and paths the app
        would put in a template, to review before `from_app`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/draft
        """
        return self._c.request_json(
            "GET", f"/v1/templates/from-app/{encode_path_param(app_id)}/draft", query={"workspace_id": workspace_id}
        )

    def stack_draft(self, stack_id: str, *, workspace_id: str | None = None) -> APITemplateDraft:
        """GET /v1/templates/from-stack/:stack_id/draft — scope `templates:write`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/draft
        """
        return self._c.request_json(
            "GET",
            f"/v1/templates/from-stack/{encode_path_param(stack_id)}/draft",
            query={"workspace_id": workspace_id},
        )

    def from_app(self, app_id: str, body: TemplateFromAppBody, *, workspace_id: str | None = None) -> APITemplateDetail:
        """POST /v1/templates/from-app/:app_id — scope `templates:write`. Saves an app you run as a private template.
        `body["workspace_id"]` is the workspace that will own the template; `workspace_id` is where the app is.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/create-from-app
        """
        return self._c.request_json(
            "POST",
            f"/v1/templates/from-app/{encode_path_param(app_id)}",
            json_body=body,
            query={"workspace_id": workspace_id},
        )

    def from_stack(
        self, stack_id: str, body: TemplateFromStackBody, *, workspace_id: str | None = None
    ) -> APITemplateDetail:
        """POST /v1/templates/from-stack/:stack_id — scope `templates:write`. Saves a stack you run as a template.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/create-from-stack
        """
        return self._c.request_json(
            "POST",
            f"/v1/templates/from-stack/{encode_path_param(stack_id)}",
            json_body=body,
            query={"workspace_id": workspace_id},
        )

    def update(
        self, template_id: str, body: TemplateUpdateDetailsBody, *, workspace_id: str | None = None
    ) -> APITemplateDetail:
        """PATCH /v1/templates/:template_id — scope `templates:write`. Changes the name, description, category
        or tags of a private template; send only what changes.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/update
        """
        return self._c.request_json(
            "PATCH", _template_path(template_id), json_body=body, query={"workspace_id": workspace_id}
        )

    def delete(self, template_id: str, *, workspace_id: str | None = None) -> None:
        """DELETE /v1/templates/:template_id — scope `templates:write`. Deletes a private template; what was
        created from it keeps running.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/delete
        """
        self._c.request_json("DELETE", _template_path(template_id), query={"workspace_id": workspace_id})

    def link_github(
        self, template_id: str, body: TemplateGithubLinkBody, *, workspace_id: str | None = None
    ) -> APITemplateDetail:
        """PUT /v1/templates/:template_id/github — scope `templates:write`. Links a repository (`owner/name`): each
        push to the branch publishes a new version from the manifest in it. `branch` is optional.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/github-link
        """
        return self._c.request_json(
            "PUT", _template_path(template_id, "/github"), json_body=body, query={"workspace_id": workspace_id}
        )

    def unlink_github(self, template_id: str, *, workspace_id: str | None = None) -> APITemplateDetail:
        """DELETE /v1/templates/:template_id/github — scope `templates:write`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/github-unlink
        """
        return self._c.request_json(
            "DELETE", _template_path(template_id, "/github"), query={"workspace_id": workspace_id}
        )

    def report_app(self, app_id: str, body: TemplateReportBody, *, workspace_id: str | None = None) -> None:
        """POST /v1/apps/:id/template/report — scope `templates:write`. Reports the template an app came from.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/templates/share-links/report
        """
        self._c.request_json(
            "POST",
            f"/v1/apps/{encode_path_param(app_id)}/template/report",
            json_body=body,
            query={"workspace_id": workspace_id},
        )
