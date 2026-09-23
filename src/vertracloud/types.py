"""Wire types, in `snake_case`. Request bodies become `TypedDict` (matching what the API
validates as its Body); responses with a published contract also become `TypedDict`, named
to match the public type contract (`APIApplication`, `APIDatabase`, ...) so cross-checking is
easier. A route with no published contract returns `JsonValue` (`Any`) — we don't invent a
shape the API doesn't guarantee.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

JsonValue = Any
JsonObject = dict[str, Any]


class EnvEntry(TypedDict, total=False):
    key: str
    value: str
    note: str | None


class SetEnvironmentEntry(TypedDict):
    key: str
    value: str


class SetEnvironmentEntryOptional(TypedDict, total=False):
    note: str | None


class SetEnvironmentBody(SetEnvironmentEntry, SetEnvironmentEntryOptional):
    """Body for `apps.envs.set` — a single `{key,value,note?}` object, or a list of them."""


EnvironmentSetBody = SetEnvironmentBody | list[SetEnvironmentBody]


class CreateAppBody(TypedDict, total=False):
    """`POST /v1/apps` — multipart. `file` is passed separately (see `AppsResource.create`)."""

    snapshot_id: str
    memory: int
    autorestart: bool
    start: str
    build: str
    main: str
    subdomain: str
    version: str
    name: str
    description: str | None
    workspace_id: str
    envs: list[EnvEntry]


class UpdateAppConfigBody(TypedDict, total=False):
    name: str
    description: str | None
    main_file: str
    version: str
    auto_restart: bool
    start_command: str | None
    build_command: str | None
    ram: int
    language: str


class RestartAppBody(TypedDict, total=False):
    cleanup_old_runtime_language: str
    reinstall_dependencies: bool
    force_build: bool


class CustomDomainBody(TypedDict):
    domain: str


class SetSubdomainBody(TypedDict):
    subdomain: str


class PublishAppBody(TypedDict, total=False):
    subdomain: str


class PurgeCacheBody(TypedDict, total=False):
    hostnames: list[str]
    paths: list[str]


class PutFileBody(TypedDict, total=False):
    path: str
    content: str
    last_modified: str
    workspace_id: str


class DeleteFileBody(TypedDict, total=False):
    path: str
    workspace_id: str


class MoveFileBody(TypedDict, total=False):
    path: str
    to: str
    workspace_id: str


class CreateWebhookBody(TypedDict):
    """Body for `apps.deploys.webhook.create` — all 4 fields are required."""

    owner: str
    repo_name: str
    repo_id: str
    account_id: str


class _CreateDatabaseBodyRequired(TypedDict):
    name: str
    ram: int


class CreateDatabaseBody(_CreateDatabaseBodyRequired, total=False):
    """`type` is only optional when `snapshot_id` is given (the engine comes from the
    snapshot); without `snapshot_id` the API requires `type`."""

    description: str | None
    type: int
    workspace_id: str
    snapshot_id: str


class UpdateDatabaseBody(TypedDict, total=False):
    name: str
    description: str | None
    ram: int


SnapshotScope = Literal["applications", "databases"]


class UpdateAccountBody(TypedDict, total=False):
    name: str
    email: str


class CreateFolderBody(TypedDict, total=False):
    name: str
    parent_id: str | None


class UpdateFolderBody(TypedDict, total=False):
    name: str
    parent_id: str | None


class CreateWorkspaceBody(TypedDict, total=False):
    name: str


class UpdateWorkspaceBody(TypedDict, total=False):
    name: str


class UpdateWorkspaceMemberBody(TypedDict, total=False):
    role_id: str


WorkspaceActionRequestAction = Literal["app_delete", "database_delete", "snapshot_create", "snapshot_restore"]
WorkspaceActionRequestStatus = Literal["pending", "approved", "rejected", "expired"]


class _CreateActionRequestBodyRequired(TypedDict):
    action: WorkspaceActionRequestAction
    resource_id: str


class CreateActionRequestBody(_CreateActionRequestBodyRequired, total=False):
    params: dict[str, Any]


class CreateRoleBody(TypedDict, total=False):
    name: str
    permissions: list[str]


class UpdateRoleBody(TypedDict, total=False):
    name: str
    permissions: list[str]


OrderType = Literal["purchase", "renew", "upgrade"]


class CreateOrderBody(TypedDict, total=False):
    plan: str
    months: int
    coupon: str
    type: OrderType
    source: str


# -- responses -------------------------------------------------------------

ApplicationLanguage = Literal[
    "javascript", "typescript", "bun", "python", "static", "php", "go", "ruby", "java", "rust"
]
ApplicationStatus = Literal["up", "down"]
ApplicationFileType = Literal["file", "directory"]
DatabaseStatus = Literal["up", "down"]
ResourceType = Literal[1, 2]
OrderStatus = Literal["unpaid", "paid", "cancelled", "expired"]


class APIApplicationShieldCooldown(TypedDict):
    until: str
    reason: Literal["burst", "rate_limit"]
    direction: Literal["in", "out"]
    strikes: int


class APIApplicationGithub(TypedDict):
    repo_owner: str
    repo_name: str


class _APIApplicationRequired(TypedDict):
    id: str
    cluster: int
    type: int
    name: str
    owner_id: str
    owner_plan_id: str
    language: ApplicationLanguage
    ram: int
    status: ApplicationStatus
    subdomain: str | None
    public_url: str | None
    custom_domain: str | None
    last_snapshot: str | None
    created_at: str
    updated_at: str
    main_file: str
    version: str
    auto_restart: bool
    start_command: str | None
    build_command: str | None
    offline_since: str | None
    shield_cooldown: APIApplicationShieldCooldown | None


class APIApplication(_APIApplicationRequired, total=False):
    description: str
    github: APIApplicationGithub | None
    missing_dependencies: list[str]


class APIApplicationNetwork(TypedDict):
    total: str
    now: str


class _APIApplicationStatusRequired(TypedDict):
    id: str
    cpu: str
    ram: str
    status: ApplicationStatus
    running: bool
    storage: str
    network: APIApplicationNetwork
    uptime: int


class APIApplicationStatus(_APIApplicationStatusRequired, total=False):
    installing: bool


class _APIApplicationStatusShortRequired(TypedDict):
    id: str
    cpu: str
    ram: str
    running: bool
    uptime: int | None


class APIApplicationStatusShort(_APIApplicationStatusShortRequired, total=False):
    installing: bool


class _APIAppFileUploadResponseRequired(TypedDict):
    app_id: str
    updated_at: str


class APIAppFileUploadResponse(_APIAppFileUploadResponseRequired, total=False):
    missing_dependencies: list[str]
    removed_directories: list[str]


class APIApplicationMetric(TypedDict):
    cpu: float
    ram: float
    storage: float
    date: str
    network: list[float]


class APIApplicationEnvironment(TypedDict):
    id: str
    key: str
    value: str
    note: str | None
    created_at: str


class APIApplicationOperationResponse(TypedDict):
    """`start`/`stop`/`restart` — generic lifecycle operation response. Same shape used by
    `databases.start`/`stop` (`APIOperationResponse`)."""

    status: str


APIOperationResponse = APIApplicationOperationResponse


class APIApplicationDeployment(TypedDict):
    app_id: str
    commit_id: str
    message: str
    pusher: str
    branch: str
    created_at: str


class APIDnsRecord(TypedDict):
    type: str
    name: str
    value: str
    status: str


class APIWebhookUrl(TypedDict):
    url: str


class APISubdomainResponse(TypedDict):
    subdomain: str


class APICustomDomainResponse(TypedDict):
    domain: str


class APIApplicationWebPublish(TypedDict):
    subdomain: str | None
    custom_domain: str | None
    type: int


class _APIApplicationFileRequired(TypedDict):
    type: ApplicationFileType
    name: str
    path: str
    last_modified: str


class APIApplicationFile(_APIApplicationFileRequired, total=False):
    size: str


class APIApplicationFileTree(APIApplicationFile, total=False):
    children: list[APIApplicationFileTree]


class APIApplicationFileContent(TypedDict):
    """`data` holds the file bytes in standard base64; `size` is the decoded length."""

    type: Literal["base64"]
    data: str
    size: int
    last_modified: str


class APIApplicationScanSuggestions(TypedDict, total=False):
    suggested_start_command: str
    suggested_build_command: str
    suggested_memory_mb: int
    suggested_public_web: bool
    missing_dependencies: list[str]


class APIRuntimeEntry(TypedDict):
    recommended: str
    latest: str
    specific: list[str]


APIRuntimesResponse = dict[str, APIRuntimeEntry]


class APIDatabase(TypedDict):
    id: str
    cluster: int
    type: int
    name: str
    description: str
    owner_id: str
    owner_plan_id: str
    status: DatabaseStatus
    ram: int
    host: str
    port: int
    created_at: str
    updated_at: str
    last_snapshot: str | None
    offline_since: str | None


class APIDatabaseNetwork(TypedDict):
    total: str
    now: str


class APIDatabaseStatus(TypedDict):
    id: str
    cpu: str
    ram: str
    status: DatabaseStatus
    running: bool
    storage: str
    network: APIDatabaseNetwork
    uptime: int


class APIDatabaseStatusShort(TypedDict):
    id: str
    cpu: str
    ram: str
    storage: str
    running: bool


class APIDatabaseMetrics(TypedDict):
    cpu: float
    ram: float
    storage: float
    date: str
    network: list[float]


class APIDatabasePasswordReset(TypedDict):
    password: str


class APIDatabaseCertificate(TypedDict):
    crt: str
    key: str
    pem: str


class APIResourceSnapshot(TypedDict):
    id: str
    resource_id: str
    author_id: str | None
    resource_type: int | None
    size: str
    date: str
    resource_name: str | None


class APIGroupedResourceSnapshots(TypedDict):
    resource_id: str
    resource_name: str | None
    type: ResourceType
    resource_type: int | None
    snapshots: list[APIResourceSnapshot]


class APISnapshotRestoreResponse(TypedDict):
    message: str


class APIUser(TypedDict):
    id: str
    name: str
    email: str
    plan_id: str
    language: str
    workspace_invites_enabled: bool
    created_at: str
    updated_at: str


class APIUserConnection(TypedDict):
    provider: str
    username: str
    created_at: str


class APIUserPlanMemory(TypedDict):
    limit: int
    used: int


class APIUserPlan(TypedDict):
    id: str
    name: str
    expires_at: str | None
    duration: int
    memory: APIUserPlanMemory


class APIWorkspaceResourceRef(TypedDict):
    resource_type: Literal["application", "database"]
    resource_id: str


class APIWorkspaceFolderItem(APIWorkspaceResourceRef):
    position: int


class APIWorkspaceResourceFolder(TypedDict):
    id: str
    name: str
    color: str
    position: int
    resources: list[APIWorkspaceFolderItem]
    created_at: str
    updated_at: str


class APIWorkspaceFavorite(APIWorkspaceResourceRef):
    position: int
    created_at: str


class APIWorkspaceResourceOrganization(TypedDict):
    scope: Literal["personal", "workspace"]
    user_id: str
    workspace_id: str | None
    folders: list[APIWorkspaceResourceFolder]
    favorites: list[APIWorkspaceFavorite]


class APIUserInfoResponse(APIUser):
    plan: APIUserPlan
    applications: list[APIApplication]
    databases: list[APIDatabase]
    connections: list[APIUserConnection]
    resource_organization: APIWorkspaceResourceOrganization


class APIUserSession(TypedDict):
    id: str
    user_id: str
    provider: str
    ip_address: str | None
    location: str | None
    device: str | None
    expires_at: str
    created_at: str
    updated_at: str
    is_current: bool


class APIWorkspaceRole(TypedDict):
    id: str
    workspace_id: str
    name: str
    permissions: list[str]
    preset: str | None
    position: int
    members_count: int
    created_at: str
    updated_at: str


class APIWorkspaceMemberUser(TypedDict):
    display_name: str
    email: str


class APIWorkspaceMember(TypedDict):
    user_id: str
    role_id: str
    role_name: str
    joined_at: str
    expires_at: str | None
    user: APIWorkspaceMemberUser


class APIWorkspaceOwner(TypedDict):
    display_name: str


class APIWorkspace(TypedDict):
    id: str
    name: str
    description: str | None
    owner_id: str
    owner: APIWorkspaceOwner
    members_count: int
    deleted_at: str | None
    frozen: bool
    created_at: str
    updated_at: str


class APIWorkspaceInfoResponse(APIWorkspace):
    members: list[APIWorkspaceMember]
    roles: list[APIWorkspaceRole]
    applications: list[APIApplication]
    databases: list[APIDatabase]
    permissions: list[str]
    is_owner: bool
    owner_plan_id: str
    resource_organization: APIWorkspaceResourceOrganization


class APIWorkspaceUserRef(TypedDict):
    id: str
    display_name: str


class APIWorkspaceInvite(TypedDict):
    id: str
    workspace_id: str
    kind: Literal["email", "link"]
    email: str | None
    role_id: str
    role_name: str
    invited_by: APIWorkspaceUserRef
    expires_at: str
    accepted_at: str | None
    revoked_at: str | None
    uses: int
    max_uses: int | None
    expires_in_days: int | None
    created_at: str


class APIWorkspaceInvitePreviewWorkspace(TypedDict):
    id: str
    name: str


class APIWorkspaceInvitePreviewInviter(TypedDict):
    display_name: str


class APIWorkspaceInvitePreview(TypedDict):
    workspace: APIWorkspaceInvitePreviewWorkspace
    inviter: APIWorkspaceInvitePreviewInviter
    role_name: str
    kind: Literal["email", "link"]
    expires_at: str


class APIWorkspaceActionRequest(TypedDict):
    id: str
    workspace_id: str
    action: WorkspaceActionRequestAction
    resource_type: Literal["application", "database"]
    resource_id: str
    resource_name: str | None
    params: dict[str, Any]
    status: WorkspaceActionRequestStatus
    requested_by: APIWorkspaceUserRef
    decided_by: APIWorkspaceUserRef | None
    decided_at: str | None
    expires_at: str
    created_at: str


class _APIOrderCreateResponseRequired(TypedDict):
    id: str
    code: str | None
    status: str
    price: float
    expires_at: str | None


class APIOrderCreateResponse(_APIOrderCreateResponseRequired, total=False):
    plan: str
    duration: int


class APIOrderStatusPlan(TypedDict):
    name: str
    months: int


class APIOrderStatusRelatedTo(TypedDict):
    plan: APIOrderStatusPlan


class APIOrderListItemPlan(TypedDict):
    name: str
    duration: int
    months: int


class APIOrderListItemRelatedTo(TypedDict):
    plan: APIOrderListItemPlan


class APIOrderStatus(TypedDict):
    id: str
    status: str
    price: float
    related_to: APIOrderStatusRelatedTo


class APIOrderListItem(TypedDict):
    id: str
    status: str
    price: float
    provider: str
    type: str
    related_to: APIOrderListItemRelatedTo
    created_at: str
    paid_at: str | None


class APIPixQrCode(TypedDict):
    copy: str | None
    base64: str | None


class APIPixPaymentResponse(TypedDict):
    transaction_amount: float | str
    external_reference: str | None
    txid: str
    qrcode: APIPixQrCode


class APIRedeemPlan(TypedDict):
    name: str
    duration: int


class APIRedeemResponse(TypedDict):
    plan: APIRedeemPlan
