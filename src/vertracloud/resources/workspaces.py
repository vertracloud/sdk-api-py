"""`workspaces` domain — 30 routes (scopes `workspaces:read/write/delete/invites`).

Creating an invite, transferring ownership, approving or rejecting an action request, and
exporting activity stay dashboard-only and have no method here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..client import encode_path_param
from ..types import (
    APIWorkspace,
    APIWorkspaceActionRequest,
    APIWorkspaceInfoResponse,
    APIWorkspaceInvite,
    APIWorkspaceInvitePreview,
    APIWorkspaceMember,
    APIWorkspaceResourceFolder,
    APIWorkspaceRole,
    CreateActionRequestBody,
    CreateFolderBody,
    CreateRoleBody,
    CreateWorkspaceBody,
    UpdateFolderBody,
    UpdateRoleBody,
    UpdateWorkspaceBody,
    UpdateWorkspaceMemberBody,
    WorkspaceActionRequestStatus,
)

if TYPE_CHECKING:
    from ..client import VertraClient


class WorkspaceMembersResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(self, workspace_id: str) -> list[APIWorkspaceMember]:
        """GET /v1/workspaces/:id/members — scope `workspaces:read`."""
        return self._c.request_json("GET", f"/v1/workspaces/{encode_path_param(workspace_id)}/members")

    def update(self, workspace_id: str, user_id: str, body: UpdateWorkspaceMemberBody) -> APIWorkspaceMember:
        """PUT /v1/workspaces/:id/members/:user_id — scope `workspaces:write`."""
        return self._c.request_json(
            "PUT",
            f"/v1/workspaces/{encode_path_param(workspace_id)}/members/{encode_path_param(user_id)}",
            json_body=body,
        )

    def remove(self, workspace_id: str, user_id: str) -> None:
        """DELETE /v1/workspaces/:id/members/:user_id — scope `workspaces:write`."""
        return self._c.request_json(
            "DELETE", f"/v1/workspaces/{encode_path_param(workspace_id)}/members/{encode_path_param(user_id)}"
        )


class WorkspaceRolesResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(self, workspace_id: str) -> list[APIWorkspaceRole]:
        """GET /v1/workspaces/:id/roles — scope `workspaces:read`."""
        return self._c.request_json("GET", f"/v1/workspaces/{encode_path_param(workspace_id)}/roles")

    def create(self, workspace_id: str, body: CreateRoleBody) -> APIWorkspaceRole:
        """POST /v1/workspaces/:id/roles — scope `workspaces:write`."""
        return self._c.request_json("POST", f"/v1/workspaces/{encode_path_param(workspace_id)}/roles", json_body=body)

    def update(self, workspace_id: str, role_id: str, body: UpdateRoleBody) -> APIWorkspaceRole:
        """PUT /v1/workspaces/:id/roles/:role_id — scope `workspaces:write`."""
        return self._c.request_json(
            "PUT",
            f"/v1/workspaces/{encode_path_param(workspace_id)}/roles/{encode_path_param(role_id)}",
            json_body=body,
        )

    def delete(self, workspace_id: str, role_id: str) -> None:
        """DELETE /v1/workspaces/:id/roles/:role_id — scope `workspaces:write`."""
        return self._c.request_json(
            "DELETE", f"/v1/workspaces/{encode_path_param(workspace_id)}/roles/{encode_path_param(role_id)}"
        )


class WorkspaceAppsResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def add(self, workspace_id: str, app_id: str) -> None:
        """POST /v1/workspaces/:id/apps/:app_id — scope `workspaces:write`."""
        return self._c.request_json(
            "POST", f"/v1/workspaces/{encode_path_param(workspace_id)}/apps/{encode_path_param(app_id)}"
        )

    def remove(self, workspace_id: str, app_id: str) -> None:
        """DELETE /v1/workspaces/:id/apps/:app_id — scope `workspaces:write`."""
        return self._c.request_json(
            "DELETE", f"/v1/workspaces/{encode_path_param(workspace_id)}/apps/{encode_path_param(app_id)}"
        )


class WorkspaceDatabasesResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def add(self, workspace_id: str, db_id: str) -> None:
        """POST /v1/workspaces/:id/databases/:db_id — scope `workspaces:write`."""
        return self._c.request_json(
            "POST", f"/v1/workspaces/{encode_path_param(workspace_id)}/databases/{encode_path_param(db_id)}"
        )

    def remove(self, workspace_id: str, db_id: str) -> None:
        """DELETE /v1/workspaces/:id/databases/:db_id — scope `workspaces:write`."""
        return self._c.request_json(
            "DELETE", f"/v1/workspaces/{encode_path_param(workspace_id)}/databases/{encode_path_param(db_id)}"
        )


class WorkspaceFoldersResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def create(self, workspace_id: str, body: CreateFolderBody) -> APIWorkspaceResourceFolder:
        """POST /v1/workspaces/:id/resource-organization/folders — scope `workspaces:write`."""
        return self._c.request_json(
            "POST", f"/v1/workspaces/{encode_path_param(workspace_id)}/resource-organization/folders", json_body=body
        )

    def update(self, workspace_id: str, folder_id: str, body: UpdateFolderBody) -> APIWorkspaceResourceFolder:
        """PATCH .../resource-organization/folders/:folder_id — scope `workspaces:write`."""
        path = (
            f"/v1/workspaces/{encode_path_param(workspace_id)}/resource-organization/folders"
            f"/{encode_path_param(folder_id)}"
        )
        return self._c.request_json("PATCH", path, json_body=body)

    def delete(self, workspace_id: str, folder_id: str) -> None:
        """DELETE .../resource-organization/folders/:folder_id — scope `workspaces:write`."""
        path = (
            f"/v1/workspaces/{encode_path_param(workspace_id)}/resource-organization/folders"
            f"/{encode_path_param(folder_id)}"
        )
        return self._c.request_json("DELETE", path)

    def add_resource(
        self,
        workspace_id: str,
        folder_id: str,
        resource_type: str,
        resource_id: str,
        *,
        position: int | None = None,
    ) -> APIWorkspaceResourceFolder:
        """PUT .../folders/:folder_id/resources/:resource_type/:resource_id — scope `workspaces:write`."""
        path = (
            f"/v1/workspaces/{encode_path_param(workspace_id)}/resource-organization/folders/{encode_path_param(folder_id)}"
            f"/resources/{encode_path_param(resource_type)}/{encode_path_param(resource_id)}"
        )
        body = {"position": position} if position is not None else {}
        return self._c.request_json("PUT", path, json_body=body)

    def remove_resource(self, workspace_id: str, folder_id: str, resource_type: str, resource_id: str) -> None:
        """DELETE .../folders/:folder_id/resources/:resource_type/:resource_id — scope `workspaces:write`."""
        path = (
            f"/v1/workspaces/{encode_path_param(workspace_id)}/resource-organization/folders/{encode_path_param(folder_id)}"
            f"/resources/{encode_path_param(resource_type)}/{encode_path_param(resource_id)}"
        )
        return self._c.request_json("DELETE", path)


class WorkspaceFavoritesResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def add(self, workspace_id: str, resource_type: str, resource_id: str, *, position: int | None = None) -> None:
        """PUT .../resource-organization/favorites/:resource_type/:resource_id — scope `workspaces:write`."""
        path = (
            f"/v1/workspaces/{encode_path_param(workspace_id)}/resource-organization/favorites"
            f"/{encode_path_param(resource_type)}/{encode_path_param(resource_id)}"
        )
        body = {"position": position} if position is not None else {}
        return self._c.request_json("PUT", path, json_body=body)

    def remove(self, workspace_id: str, resource_type: str, resource_id: str) -> None:
        """DELETE .../resource-organization/favorites/:resource_type/:resource_id — scope `workspaces:write`."""
        path = (
            f"/v1/workspaces/{encode_path_param(workspace_id)}/resource-organization/favorites"
            f"/{encode_path_param(resource_type)}/{encode_path_param(resource_id)}"
        )
        return self._c.request_json("DELETE", path)


class WorkspaceInvitesResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(self, workspace_id: str) -> list[APIWorkspaceInvite]:
        """GET /v1/workspaces/:id/invites — scope `workspaces:invites`."""
        return self._c.request_json("GET", f"/v1/workspaces/{encode_path_param(workspace_id)}/invites")

    def revoke(self, workspace_id: str, invite_id: str) -> None:
        """DELETE /v1/workspaces/:id/invites/:invite_id — scope `workspaces:invites`."""
        return self._c.request_json(
            "DELETE", f"/v1/workspaces/{encode_path_param(workspace_id)}/invites/{encode_path_param(invite_id)}"
        )

    def preview(self, token: str) -> APIWorkspaceInvitePreview:
        """GET /v1/workspaces/invites/:token — scope `workspaces:invites`. What the invite grants, before accepting."""
        return self._c.request_json("GET", f"/v1/workspaces/invites/{encode_path_param(token)}")

    def accept(self, token: str) -> APIWorkspace:
        """POST /v1/workspaces/invites/:token/accept — scope `workspaces:invites`. Returns the workspace."""
        return self._c.request_json("POST", f"/v1/workspaces/invites/{encode_path_param(token)}/accept")

    def decline(self, token: str) -> None:
        """POST /v1/workspaces/invites/:token/decline — scope `workspaces:invites`."""
        return self._c.request_json("POST", f"/v1/workspaces/invites/{encode_path_param(token)}/decline")


class WorkspaceActionRequestsResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(
        self, workspace_id: str, *, status: WorkspaceActionRequestStatus | None = None
    ) -> list[APIWorkspaceActionRequest]:
        """GET /v1/workspaces/:id/action-requests — scope `workspaces:read`. `status` filters the list."""
        return self._c.request_json(
            "GET", f"/v1/workspaces/{encode_path_param(workspace_id)}/action-requests", query={"status": status}
        )

    def create(self, workspace_id: str, body: CreateActionRequestBody) -> APIWorkspaceActionRequest:
        """POST /v1/workspaces/:id/action-requests — scope `workspaces:write`. Asks a member with
        the required permission to approve an action you cannot perform yourself."""
        return self._c.request_json(
            "POST", f"/v1/workspaces/{encode_path_param(workspace_id)}/action-requests", json_body=body
        )


class WorkspacesResource:
    """`workspaces.*` — list/get/create/update/delete + `members`, `roles`, `invites`,
    `action_requests`, `apps`, `databases`, `folders`, `favorites`."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client
        self.members = WorkspaceMembersResource(client)
        self.roles = WorkspaceRolesResource(client)
        self.invites = WorkspaceInvitesResource(client)
        self.action_requests = WorkspaceActionRequestsResource(client)
        self.apps = WorkspaceAppsResource(client)
        self.databases = WorkspaceDatabasesResource(client)
        self.folders = WorkspaceFoldersResource(client)
        self.favorites = WorkspaceFavoritesResource(client)

    def list(self) -> list[APIWorkspace]:
        """GET /v1/workspaces — scope `workspaces:read`."""
        return self._c.request_json("GET", "/v1/workspaces")

    def get(self, workspace_id: str) -> APIWorkspaceInfoResponse:
        """GET /v1/workspaces/:id — scope `workspaces:read`."""
        return self._c.request_json("GET", f"/v1/workspaces/{encode_path_param(workspace_id)}")

    def create(self, body: CreateWorkspaceBody) -> APIWorkspace:
        """POST /v1/workspaces — scope `workspaces:write`."""
        return self._c.request_json("POST", "/v1/workspaces", json_body=body)

    def update(self, workspace_id: str, body: UpdateWorkspaceBody) -> APIWorkspace:
        """PUT /v1/workspaces/:id — scope `workspaces:write`."""
        return self._c.request_json("PUT", f"/v1/workspaces/{encode_path_param(workspace_id)}", json_body=body)

    def delete(self, workspace_id: str) -> None:
        """DELETE /v1/workspaces/:id — scope `workspaces:delete`, owner only. Soft delete."""
        return self._c.request_json("DELETE", f"/v1/workspaces/{encode_path_param(workspace_id)}")
