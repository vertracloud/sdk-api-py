"""`account` domain — 10 routes (scopes `account:read/write`).

The user's activity log is website-only — there is no corresponding method here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..client import encode_path_param
from ..types import (
    APIUserInfoResponse,
    APIUserSession,
    APIWorkspaceResourceFolder,
    CreateFolderBody,
    UpdateAccountBody,
    UpdateFolderBody,
)

if TYPE_CHECKING:
    from ..client import VertraClient


class AccountSessionsResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(self) -> list[APIUserSession]:
        """GET /v1/users/me/sessions — scope `account:read`."""
        return self._c.request_json("GET", "/v1/users/me/sessions")


class AccountFoldersResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def create(self, body: CreateFolderBody) -> APIWorkspaceResourceFolder:
        """POST /v1/users/me/folders — scope `account:write`."""
        return self._c.request_json("POST", "/v1/users/me/folders", json_body=body)

    def update(self, folder_id: str, body: UpdateFolderBody) -> APIWorkspaceResourceFolder:
        """PATCH /v1/users/me/folders/:folder_id — scope `account:write`."""
        return self._c.request_json(
            "PATCH", f"/v1/users/me/folders/{encode_path_param(folder_id)}", json_body=body
        )

    def delete(self, folder_id: str) -> None:
        """DELETE /v1/users/me/folders/:folder_id — scope `account:write`."""
        return self._c.request_json(
            "DELETE", f"/v1/users/me/folders/{encode_path_param(folder_id)}"
        )

    def add_resource(
        self, folder_id: str, resource_type: str, resource_id: str, *, position: int | None = None
    ) -> APIWorkspaceResourceFolder:
        """PUT .../folders/:folder_id/resources/:resource_type/:resource_id — scope `account:write`."""
        path = (
            f"/v1/users/me/folders/{encode_path_param(folder_id)}"
            f"/resources/{encode_path_param(resource_type)}/{encode_path_param(resource_id)}"
        )
        body = {"position": position} if position is not None else {}
        return self._c.request_json("PUT", path, json_body=body)

    def remove_resource(self, folder_id: str, resource_type: str, resource_id: str) -> None:
        """DELETE .../folders/:folder_id/resources/:resource_type/:resource_id — scope `account:write`."""
        path = (
            f"/v1/users/me/folders/{encode_path_param(folder_id)}"
            f"/resources/{encode_path_param(resource_type)}/{encode_path_param(resource_id)}"
        )
        return self._c.request_json("DELETE", path)


class AccountFavoritesResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def add(self, resource_type: str, resource_id: str, *, position: int | None = None) -> None:
        """PUT /v1/users/me/favorites/:resource_type/:resource_id — `account:write`."""
        path = (
            f"/v1/users/me/favorites/{encode_path_param(resource_type)}"
            f"/{encode_path_param(resource_id)}"
        )
        body = {"position": position} if position is not None else {}
        return self._c.request_json("PUT", path, json_body=body)

    def remove(self, resource_type: str, resource_id: str) -> None:
        """DELETE .../favorites/:resource_type/:resource_id — scope `account:write`."""
        path = (
            f"/v1/users/me/favorites/{encode_path_param(resource_type)}"
            f"/{encode_path_param(resource_id)}"
        )
        return self._c.request_json("DELETE", path)


class AccountResource:
    """`account.*` — get/update, `sessions`, `folders`, `favorites`."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client
        self.sessions = AccountSessionsResource(client)
        self.folders = AccountFoldersResource(client)
        self.favorites = AccountFavoritesResource(client)

    def get(self) -> APIUserInfoResponse:
        """GET /v1/users/me — scope `account:read`. There is no `GET /v1/apps` or `/v1/databases`:
        the user's list of apps/databases comes from here (`applications[]`, `databases[]`) or
        from `apps.status_all()`/`databases.status_all()`."""
        return self._c.request_json("GET", "/v1/users/me")

    def update(self, body: UpdateAccountBody) -> APIUserInfoResponse:
        """PATCH /v1/users/me — scope `account:write`."""
        return self._c.request_json("PATCH", "/v1/users/me", json_body=body)
