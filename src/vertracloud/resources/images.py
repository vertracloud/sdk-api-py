"""`images` domain — custom Docker images (scopes `images:read`, `images:write` and `images:delete`).

A custom image is a build context with a `Dockerfile`, built by the platform in isolation.
`apps.create_from_image` (scope `apps:write`) runs an app from a ready image. Create and rebuild
reply 202 with `status: "building"`: follow the build with `logs`, or poll `get` until `status`
is `success` or `failed`.

`workspace_id` is a keyword-only query parameter on the routes that act on an existing image and
on `list`. Without it the call acts on the caller's own images, as the apps routes do.

An image that came from a template (`kind == "template_copy"`, or a platform image) cannot be renamed, rebuilt,
linked to GitHub or committed to: those calls fail with `IMAGE_TEMPLATE_ONLY`. Deleting an image that is the
source of one of your private templates fails with `IMAGE_IN_USE`.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from ..client import LARGE_PAYLOAD_TIMEOUT, MultipartField, encode_path_param
from ..sse import SseStream
from ..types import (
    APICustomImage,
    APICustomImageContext,
    APICustomImageDeleteResult,
    APICustomImageVersion,
    APIDockerfileCheck,
    CheckDockerfileBody,
    CreateCustomImageBody,
    CustomImageGithubBody,
    UpdateCustomImageBody,
)

if TYPE_CHECKING:
    from ..client import VertraClient

# Aliases so `list[...]` doesn't resolve to the `list` method inside the class itself.
ImageList = list[APICustomImage]
ImageVersionList = list[APICustomImageVersion]


class ImageLogStream:
    """Build log of an image, as lines. Iterate it for the text of each `log` event; `close()`
    stops following a live build. Other events (`system`, `heartbeat`) are skipped."""

    def __init__(self, stream: SseStream) -> None:
        self._stream = stream

    def __iter__(self) -> Iterator[str]:
        for event in self._stream:
            if event.event == "log":
                yield event.data

    def close(self) -> None:
        self._stream.close()


class ImagesResource:
    """`images.*` — list/get/create/update/rebuild/delete/versions/logs/context/link_github/unlink_github/check."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(self, *, workspace_id: str | None = None) -> ImageList:
        """GET /v1/images — scope `images:read`. With `workspace_id`, lists the images of that workspace.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/images/list
        """
        return self._c.request_json("GET", "/v1/images", query={"workspace_id": workspace_id})

    def get(self, image_id: str, *, workspace_id: str | None = None) -> APICustomImage:
        """GET /v1/images/:image_id — scope `images:read`. `status` is the state of the latest build;
        `current_version_id` and `digest` are `None` until a build succeeds.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/images/get
        """
        return self._c.request_json(
            "GET", f"/v1/images/{encode_path_param(image_id)}", query={"workspace_id": workspace_id}
        )

    def create(
        self,
        body: CreateCustomImageBody,
        *,
        file: bytes | None = None,
        filename: str = "image.zip",
        timeout: float | None = None,
    ) -> APICustomImage:
        """POST /v1/images — scope `images:write`. Multipart. The source is either `file` (a ZIP
        of up to 100 MB, with a `Dockerfile` at its root) or `body["github_repository"]`;
        `body["github_branch"]` is optional (default: the repository's default branch). A repository
        in your GitHub App installations is linked and each push to the branch rebuilds the image; a
        public repository outside them is built once, with no link (`github` is `None`). Raises
        `ValueError` before any request when the source is missing, doubled, or a branch comes without
        a repository. Replies 202 with `status: "building"`.
        Errors: `PLAN_DOES_NOT_SUPPORT_CUSTOM_IMAGES`, `MAX_IMAGES_REACHED`, `DOCKERFILE_NOT_FOUND`,
        `DOCKERFILE_REFUSED` (its `issues` attribute lists the findings), `IMAGE_CONTEXT_TOO_LARGE`,
        `IMAGE_BUILDER_UNAVAILABLE`, `INSTALLATION_NOT_FOUND` (a private or missing repository outside
        your installations).
        Doc: https://docs.vertracloud.app/api-reference/endpoint/images/create
        """
        repository = body.get("github_repository")
        branch = body.get("github_branch")
        if file is not None and (repository is not None or branch is not None):
            raise ValueError("pass either file or github_repository (with github_branch), not both")
        if file is None and repository is None:
            raise ValueError("pass file, or github_repository (with an optional github_branch)")

        fields = [MultipartField("name", body["name"])]
        description = body.get("description")
        if description is not None:
            fields.append(MultipartField("description", description))
        if file is not None:
            fields.append(MultipartField("file", file, filename=filename))
        if repository is not None:
            fields.append(MultipartField("github_repository", repository))
        if branch is not None:
            fields.append(MultipartField("github_branch", branch))
        workspace_id = body.get("workspace_id")
        if workspace_id is not None:
            fields.append(MultipartField("workspace_id", workspace_id))
        return self._c.request_multipart(
            "POST", "/v1/images", fields=fields, timeout=timeout if timeout is not None else LARGE_PAYLOAD_TIMEOUT
        )

    def update(self, image_id: str, body: UpdateCustomImageBody, *, workspace_id: str | None = None) -> APICustomImage:
        """PATCH /v1/images/:image_id — scope `images:write`. Renames the image and/or changes its
        description; send only what changes (`description: None` or an empty string removes it). Builds
        nothing: the apps keep running and nothing restarts. Errors: `VALIDATION_ERROR` (empty body, name
        out of range or already used by another of your images with `details.path == "name"`,
        description too long), `IMAGE_NOT_FOUND`, `ACCESS_DENIED` (system images cannot be changed).
        Doc: https://docs.vertracloud.app/api-reference/endpoint/images/update
        """
        return self._c.request_json(
            "PATCH",
            f"/v1/images/{encode_path_param(image_id)}",
            json_body=body,
            query={"workspace_id": workspace_id},
        )

    def rebuild(
        self,
        image_id: str,
        *,
        file: bytes,
        filename: str = "image.zip",
        workspace_id: str | None = None,
        timeout: float | None = None,
    ) -> APICustomImage:
        """PUT /v1/images/:image_id — scope `images:write`. Multipart `file` replaces the whole build
        context. Replies 202 with `status: "building"`. Refused with `IMAGE_BUILD_IN_PROGRESS` while a
        build runs. A rebuild never restarts the apps that run the image.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/images/rebuild
        """
        return self._c.request_multipart(
            "PUT",
            f"/v1/images/{encode_path_param(image_id)}",
            fields=[MultipartField("file", file, filename=filename)],
            query={"workspace_id": workspace_id},
            timeout=timeout if timeout is not None else LARGE_PAYLOAD_TIMEOUT,
        )

    def delete(
        self, image_id: str, *, confirm_name: str, workspace_id: str | None = None
    ) -> APICustomImageDeleteResult:
        """DELETE /v1/images/:image_id — scope `images:delete`, and also `apps:delete` when apps run the
        image. Body `{confirm_name}` must equal the image name (`IMAGE_NAME_MISMATCH` otherwise).
        Deletes the versions, the context and every app created from the image; `deleted_apps` lists
        their ids. Refused with `IMAGE_BUILD_IN_PROGRESS` while a build runs.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/images/delete
        """
        return self._c.request_json(
            "DELETE",
            f"/v1/images/{encode_path_param(image_id)}",
            json_body={"confirm_name": confirm_name},
            query={"workspace_id": workspace_id},
        )

    def versions(self, image_id: str, *, workspace_id: str | None = None) -> ImageVersionList:
        """GET /v1/images/:image_id/versions — scope `images:read`. Newest first.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/images/versions
        """
        return self._c.request_json(
            "GET", f"/v1/images/{encode_path_param(image_id)}/versions", query={"workspace_id": workspace_id}
        )

    def logs(
        self,
        image_id: str,
        *,
        version_id: str | None = None,
        workspace_id: str | None = None,
        timeout: float | None = None,
    ) -> ImageLogStream:
        """GET /v1/images/:image_id/logs — scope `images:read`. A Server-Sent Events stream: it repeats
        the history of the build and then follows it live. `version_id` picks the build of one version;
        by default it is the latest build. Iterate it for lines; `close()` or `break` ends it.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/images/logs
        """
        stream = self._c.request_sse(
            f"/v1/images/{encode_path_param(image_id)}/logs",
            query={"version_id": version_id, "workspace_id": workspace_id},
            timeout=timeout,
        )
        return ImageLogStream(stream)

    def context(self, image_id: str, *, workspace_id: str | None = None) -> APICustomImageContext:
        """GET /v1/images/:image_id/context — scope `images:read`. `url` is a temporary download link
        of the current build context.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/images/context
        """
        return self._c.request_json(
            "GET", f"/v1/images/{encode_path_param(image_id)}/context", query={"workspace_id": workspace_id}
        )

    def link_github(
        self, image_id: str, body: CustomImageGithubBody, *, workspace_id: str | None = None
    ) -> APICustomImage:
        """PUT /v1/images/:image_id/github — scope `images:write`. Links a repository (`owner/name`) in
        your GitHub App installations: each push to the branch rebuilds the image. `body["branch"]` is
        optional (default: the repository's default branch).
        Doc: https://docs.vertracloud.app/api-reference/endpoint/images/github-link
        """
        return self._c.request_json(
            "PUT",
            f"/v1/images/{encode_path_param(image_id)}/github",
            json_body=body,
            query={"workspace_id": workspace_id},
        )

    def unlink_github(self, image_id: str, *, workspace_id: str | None = None) -> APICustomImage:
        """DELETE /v1/images/:image_id/github — scope `images:write`. Unlinks the repository.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/images/github-unlink
        """
        return self._c.request_json(
            "DELETE", f"/v1/images/{encode_path_param(image_id)}/github", query={"workspace_id": workspace_id}
        )

    def check(self, body: CheckDockerfileBody) -> APIDockerfileCheck:
        """POST /v1/images/check — scope `images:read`. Checks a `Dockerfile` and the paths of its
        context before building; creates nothing. `refusals` would block the build, `warnings` would not.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/images/check
        """
        return self._c.request_json("POST", "/v1/images/check", json_body=body)
