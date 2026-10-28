"""`stacks` domain — groups of applications, databases and Blob folders that stay connected (scopes `stacks:read`,
`stacks:write` and `stacks:delete`).

A stack keeps the connection variables of each application up to date. Changes that alter variables or
certificates answer with `restart_required` and `apps_to_restart`: an application reads them only when it
starts, so the restart is yours to ask for (`apps.restart`).

`workspace_id` is a keyword-only query parameter on the routes that read or change an existing stack, and on
`list`; the routes that create a stack take it in the body. Without it the call acts on the caller's own stacks.
Moving a stack to a workspace and back is `workspaces.stacks`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..client import encode_path_param
from ..types import (
    APIRestartRequired,
    APISnapshotRestoreResponse,
    APIStack,
    APIStackBinding,
    APIStackBindingChange,
    APIStackBlobAdded,
    APIStackChange,
    APIStackConnectionInfo,
    APIStackDatabaseAdded,
    APIStackDeleteResult,
    APIStackSnapshot,
    ApplicationLanguage,
    StackBindingCreateBody,
    StackBindingRemoval,
    StackBindingValue,
    StackBlobBody,
    StackBlobDisposition,
    StackCreateBody,
    StackDatabaseBody,
    StackDeleteBody,
    StackMemberAddBody,
    StackMemberType,
    StackNetworkMode,
    StackTransformBody,
    StackUpdateBody,
)

if TYPE_CHECKING:
    from ..client import VertraClient

# Aliases so `list[...]` doesn't resolve to the `list` method inside the class itself.
StackList = list[APIStack]
StackBindingList = list[APIStackBinding]
StackSnapshotList = list[APIStackSnapshot]


def _stack_path(stack_id: str, suffix: str = "") -> str:
    return f"/v1/stacks/{encode_path_param(stack_id)}{suffix}"


class StackMembersResource:
    """`stacks.members.*` — add/remove."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def add(self, stack_id: str, body: StackMemberAddBody, *, workspace_id: str | None = None) -> APIStackChange:
        """POST /v1/stacks/:stack_id/members — scope `stacks:write`. Adds an application or a database you already
        have (in the same account or workspace, and not in another stack); `body["bindings"]` connects it on the way.
        Errors: `STACK_MEMBER_CONFLICT`, `STACK_NETWORK_MODE_UNAVAILABLE`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/members/add
        """
        return self._c.request_json(
            "POST", _stack_path(stack_id, "/members"), json_body=body, query={"workspace_id": workspace_id}
        )

    def remove(
        self,
        stack_id: str,
        resource_type: StackMemberType,
        resource_id: str,
        *,
        bindings: StackBindingRemoval | None = None,
        blob: StackBlobDisposition | None = None,
        workspace_id: str | None = None,
    ) -> APIStackChange:
        """DELETE /v1/stacks/:stack_id/members/:resource_type/:resource_id — scope `stacks:write`. Takes the member
        out of the stack; the resource itself stays. `bindings` says what happens to its connections
        (`keep_connection` or `remove_variables`); `blob` says what happens to the files of a Blob folder
        (`keep` or `delete`). Errors: `STACK_MEMBER_NOT_FOUND`, `STACK_SERVICE_LOCKED`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/members/remove
        """
        return self._c.request_json(
            "DELETE",
            _stack_path(stack_id, f"/members/{encode_path_param(resource_type)}/{encode_path_param(resource_id)}"),
            query={"bindings": bindings, "blob": blob, "workspace_id": workspace_id},
        )


class StackBindingsResource:
    """`stacks.bindings.*` — list/create/update/delete the connections between the members of a stack."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(self, stack_id: str, *, workspace_id: str | None = None) -> StackBindingList:
        """GET /v1/stacks/:stack_id/bindings — scope `stacks:read`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/bindings/list
        """
        return self._c.request_json("GET", _stack_path(stack_id, "/bindings"), query={"workspace_id": workspace_id})

    def create(
        self, stack_id: str, body: StackBindingCreateBody, *, workspace_id: str | None = None
    ) -> APIStackBindingChange:
        """POST /v1/stacks/:stack_id/bindings — scope `stacks:write`. Connects an application (`app_id`) to a
        database (`database_id`), a Blob folder (`blob_id`) or another application (`target_app_id`); `env_map`
        names the variables that receive each value.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/bindings/create
        """
        return self._c.request_json(
            "POST", _stack_path(stack_id, "/bindings"), json_body=body, query={"workspace_id": workspace_id}
        )

    def update(
        self,
        stack_id: str,
        binding_id: str,
        env_map: dict[str, StackBindingValue],
        *,
        workspace_id: str | None = None,
    ) -> APIStackBindingChange:
        """PATCH /v1/stacks/:stack_id/bindings/:binding_id — scope `stacks:write`. Replaces the variable map of the
        connection. Errors: `STACK_BINDING_NOT_FOUND`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/bindings/update
        """
        return self._c.request_json(
            "PATCH",
            _stack_path(stack_id, f"/bindings/{encode_path_param(binding_id)}"),
            json_body={"env_map": env_map},
            query={"workspace_id": workspace_id},
        )

    def delete(
        self,
        stack_id: str,
        binding_id: str,
        *,
        variables: StackBindingRemoval | None = None,
        workspace_id: str | None = None,
    ) -> APIRestartRequired:
        """DELETE /v1/stacks/:stack_id/bindings/:binding_id — scope `stacks:write`. `variables` says whether the
        variables the connection managed are kept as ordinary ones or removed.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/bindings/delete
        """
        return self._c.request_json(
            "DELETE",
            _stack_path(stack_id, f"/bindings/{encode_path_param(binding_id)}"),
            query={"variables": variables, "workspace_id": workspace_id},
        )


class StackSnapshotsResource:
    """`stacks.snapshots.*` — snapshots of the whole stack (every application and database at once)."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(self, stack_id: str, *, workspace_id: str | None = None) -> StackSnapshotList:
        """GET /v1/stacks/:stack_id/snapshots — scope `stacks:read`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/snapshots/list
        """
        return self._c.request_json("GET", _stack_path(stack_id, "/snapshots"), query={"workspace_id": workspace_id})

    def create(self, stack_id: str, *, workspace_id: str | None = None) -> APIStackSnapshot:
        """POST /v1/stacks/:stack_id/snapshots — scope `stacks:write`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/snapshots/create
        """
        return self._c.request_json("POST", _stack_path(stack_id, "/snapshots"), query={"workspace_id": workspace_id})

    def restore(
        self,
        stack_id: str,
        snapshot_id: str,
        *,
        restore_image_version: bool | None = None,
        workspace_id: str | None = None,
    ) -> APISnapshotRestoreResponse:
        """POST /v1/stacks/:stack_id/snapshots/:snapshot_id/restore — scope `stacks:write`. Restores every member.
        `restore_image_version=True` also goes back to the image version recorded in the snapshot.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/snapshots/restore
        """
        body = {"restore_image_version": restore_image_version} if restore_image_version is not None else None
        return self._c.request_json(
            "POST",
            _stack_path(stack_id, f"/snapshots/{encode_path_param(snapshot_id)}/restore"),
            json_body=body,
            query={"workspace_id": workspace_id},
        )


class StacksResource:
    """`stacks.*` — list/get/create/transform/update/delete/connection/set_network_mode/add_database/
    add_database_to_app/add_blob, and the sub-resources `members`, `bindings` and `snapshots`."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client
        self.members = StackMembersResource(client)
        self.bindings = StackBindingsResource(client)
        self.snapshots = StackSnapshotsResource(client)

    def list(self, *, workspace_id: str | None = None) -> StackList:
        """GET /v1/stacks — scope `stacks:read`. With `workspace_id`, lists the stacks of that workspace.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/list
        """
        return self._c.request_json("GET", "/v1/stacks", query={"workspace_id": workspace_id})

    def get(self, stack_id: str, *, workspace_id: str | None = None) -> APIStack:
        """GET /v1/stacks/:stack_id — scope `stacks:read`. Errors: `STACK_NOT_FOUND`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/get
        """
        return self._c.request_json("GET", _stack_path(stack_id), query={"workspace_id": workspace_id})

    def create(self, body: StackCreateBody) -> APIStackChange:
        """POST /v1/stacks — scope `stacks:write`. Groups applications and databases that already exist, all in the
        same account or workspace and not in another stack; `body["bindings"]` connects them.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/create
        """
        return self._c.request_json("POST", "/v1/stacks", json_body=body)

    def transform(self, body: StackTransformBody) -> APIStackChange:
        """POST /v1/stacks/transform — scope `stacks:write`. Turns the applications and databases of a folder into a
        stack (`STACK_TRANSFORM_EMPTY` when the folder has none). `inject_variables` says whether the connection
        variables are written into the applications.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/transform
        """
        return self._c.request_json("POST", "/v1/stacks/transform", json_body=body)

    def update(self, stack_id: str, body: StackUpdateBody, *, workspace_id: str | None = None) -> APIStack:
        """PATCH /v1/stacks/:stack_id — scope `stacks:write`. Renames the stack or changes its description.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/update
        """
        return self._c.request_json(
            "PATCH", _stack_path(stack_id), json_body=body, query={"workspace_id": workspace_id}
        )

    def delete(self, stack_id: str, body: StackDeleteBody, *, workspace_id: str | None = None) -> APIStackDeleteResult:
        """DELETE /v1/stacks/:stack_id — scope `stacks:delete`. `body["confirm_name"]` must equal the stack name
        (`STACK_NAME_MISMATCH` otherwise). `mode` `dissolve` removes only the stack; `delete_all` deletes the
        members too. `blob` says what happens to the files of the stack's Blob folder.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/delete
        """
        return self._c.request_json(
            "DELETE", _stack_path(stack_id), json_body=body, query={"workspace_id": workspace_id}
        )

    def connection(
        self,
        stack_id: str,
        *,
        app_id: str,
        language: ApplicationLanguage | None = None,
        workspace_id: str | None = None,
    ) -> APIStackConnectionInfo:
        """GET /v1/stacks/:stack_id/connection — scope `stacks:read`. Code snippets that connect `app_id` to what it
        is linked to; `language` defaults to the language of the app.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/connection
        """
        return self._c.request_json(
            "GET",
            _stack_path(stack_id, "/connection"),
            query={"app_id": app_id, "language": language, "workspace_id": workspace_id},
        )

    def set_network_mode(
        self, stack_id: str, network_mode: StackNetworkMode, *, workspace_id: str | None = None
    ) -> APIStack:
        """POST /v1/stacks/:stack_id/network-mode — scope `stacks:write`. `public` or `private`; a mode the plan
        does not offer fails with `STACK_NETWORK_MODE_UNAVAILABLE`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/network-mode
        """
        return self._c.request_json(
            "POST",
            _stack_path(stack_id, "/network-mode"),
            json_body={"network_mode": network_mode},
            query={"workspace_id": workspace_id},
        )

    def add_database(
        self, stack_id: str, body: StackDatabaseBody, *, workspace_id: str | None = None
    ) -> APIStackDatabaseAdded:
        """POST /v1/stacks/:stack_id/databases — scope `stacks:write`. Creates a database inside the stack and
        connects the applications in `body["bindings"]` to it.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/databases/create
        """
        return self._c.request_json(
            "POST", _stack_path(stack_id, "/databases"), json_body=body, query={"workspace_id": workspace_id}
        )

    def add_database_to_app(
        self, app_id: str, body: StackDatabaseBody, *, workspace_id: str | None = None
    ) -> APIStackDatabaseAdded:
        """POST /v1/apps/:id/stack/databases — scope `stacks:write`. "Add database" from an application: creates
        the database and puts both in a stack (the one the app is in, or a new one named `body["stack_name"]`).
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/databases/create
        """
        return self._c.request_json(
            "POST",
            f"/v1/apps/{encode_path_param(app_id)}/stack/databases",
            json_body=body,
            query={"workspace_id": workspace_id},
        )

    def add_blob(
        self, stack_id: str, body: StackBlobBody | None = None, *, workspace_id: str | None = None
    ) -> APIStackBlobAdded:
        """POST /v1/stacks/:stack_id/blob — scope `stacks:write`. Gives the stack a Blob folder with its own
        restricted API key (an API key with `blob_prefix`, managed by the stack). Without `prefix` the platform
        picks `stacks/<stack-slug>/`; a taken explicit prefix fails with `STACK_BLOB_PREFIX_TAKEN`.
        Doc: https://docs.vertracloud.app/api-reference/endpoint/stacks/blob/create
        """
        return self._c.request_json(
            "POST",
            _stack_path(stack_id, "/blob"),
            json_body=body if body is not None else {},
            query={"workspace_id": workspace_id},
        )
