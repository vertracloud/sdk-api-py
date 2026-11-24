"""Wire types, in `snake_case`. Request bodies become `TypedDict` (matching what the API
validates as its Body); responses with a published contract also become `TypedDict`, named
to match the public type contract (`APIApplication`, `APIDatabase`, ...) so cross-checking is
easier. A route with no published contract returns `JsonValue` (`Any`) — we don't invent a
shape the API doesn't guarantee.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

PlanFamily = Literal["starter", "pro", "business", "enterprise"]

PlanName = Literal[
    "starter-1",
    "starter-2",
    "pro-4",
    "pro-6",
    "pro-8",
    "business-12",
    "business-16",
    "business-24",
    "enterprise-32",
    "enterprise-48",
    "enterprise-64",
    "enterprise-96",
    "enterprise-128",
    "enterprise-160",
    "enterprise-192",
    "enterprise-224",
    "enterprise-256",
    "enterprise-288",
    "enterprise-320",
    "enterprise-384",
    "enterprise-448",
    "enterprise-512",
]

# Billing period in months.
BillingMonths = Literal[1, 3, 6, 12]

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
    start: str
    build: str
    main: str
    subdomain: str
    version: str
    language: ApplicationLanguage
    name: str
    description: str | None
    workspace_id: str
    envs: list[EnvEntry]
    auto_restart: bool
    """Restart the app by itself when it stops on its own. Omitted, the API uses `True`."""


ApplicationZeroDowntime = Literal["auto", "on", "off"]


class UpdateAppDeployBody(TypedDict, total=False):
    """`deploy` in `PATCH /v1/apps/:id/config`. Omit a key to leave it unchanged;
    `health_check_path: None` is sent as JSON `null` and clears the path (back to `/`)."""

    zero_downtime: ApplicationZeroDowntime
    auto_rollback: bool
    health_check_path: str | None


class UpdateAppConfigBody(TypedDict, total=False):
    name: str
    description: str | None
    main_file: str
    version: str
    start_command: str | None
    build_command: str | None
    ram: int
    language: str
    deploy: UpdateAppDeployBody
    auto_restart: bool


class RollbackAppBody(TypedDict, total=False):
    """Body of `POST /v1/apps/:id/releases/:release_id/rollback`."""

    restore_environment: bool


class RestartAppBody(TypedDict, total=False):
    reinstall_dependencies: bool
    force_build: bool


ApplicationDomainStatus = Literal["pending", "active", "moved", "deleted"]
ApplicationDomainSslStatus = Literal["pending", "active", "failed"]
ApplicationDomainRedirectStatus = Literal[301, 302, 307, 308]


class _AddDomainRequired(TypedDict):
    hostname: str


class AddDomainBody(_AddDomainRequired, total=False):
    """`POST /v1/apps/:id/domains`. `www` defaults to `True` on the server; `redirect_status`
    only applies with `redirect_to`."""

    www: bool
    port: int
    path_prefix: str
    redirect_to: str
    redirect_status: ApplicationDomainRedirectStatus


class UpdateDomainBody(TypedDict, total=False):
    """`PATCH /v1/apps/:id/domains/:domain_id`. Send only what changes; `None` clears `path_prefix`
    or `redirect_to`. `primary=True` swaps the domain with its companion as the main one."""

    port: int
    path_prefix: str | None
    redirect_to: str | None
    redirect_status: ApplicationDomainRedirectStatus
    primary: Literal[True]


class SetSubdomainBody(TypedDict):
    subdomain: str


class PublishAppBody(TypedDict, total=False):
    subdomain: str
    # Only for an app on a custom image: the port the image listens on (1-65535).
    # Required when the app was created without web; ignored for other apps.
    port: int


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
    confirm_detach: bool


class MoveFileBody(TypedDict, total=False):
    path: str
    to: str
    workspace_id: str
    # Confirms that the change detaches an app of an open template from it (`TEMPLATE_DETACH_CONFIRMATION_REQUIRED`).
    confirm_detach: bool


class _CreateWebhookBodyRequired(TypedDict):
    owner: str
    repo_name: str
    repo_id: str
    account_id: str


class CreateWebhookBody(_CreateWebhookBodyRequired, total=False):
    """Body for `apps.deploys.webhook.create` — the first 4 fields are required.

    `branch` is the only branch the auto-deploy reacts to. Without it, a push on `main` or `master`
    deploys, as it always did. Linking again with another `branch` changes it; linking again
    without one goes back to `main` or `master`.

    `confirm_detach` confirms that the change detaches an app of an open template from it."""

    branch: str
    confirm_detach: bool


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
    version: str
    """Engine major line (see `databases.versions()`). Omitted, the recommended one is used; with
    `snapshot_id`, omit it to keep the snapshot's line (an older one fails with `SNAPSHOT_VERSION_NEWER`,
    an unknown one with `INVALID_DATABASE_VERSION`)."""


class UpdateDatabaseBody(TypedDict, total=False):
    name: str
    description: str | None
    ram: int


SnapshotScope = Literal["applications", "databases"]


class UpdateAccountBody(TypedDict, total=False):
    name: str
    email: str


class WorkspaceFolderFlowLayout(TypedDict, total=False):
    """Position of a folder on the Flow canvas."""

    x: float
    y: float
    collapsed: bool


class CreateFolderBody(TypedDict, total=False):
    name: str
    parent_id: str | None
    # Free-text notes; `None` removes them (on update).
    notes: str | None
    # Position on the Flow canvas; `None` removes it (on update).
    flow_layout: WorkspaceFolderFlowLayout | None


class UpdateFolderBody(TypedDict, total=False):
    name: str
    parent_id: str | None
    notes: str | None
    flow_layout: WorkspaceFolderFlowLayout | None


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
OrderProvider = Literal["pix", "card", "redeem_code"]


class CreateOrderBody(TypedDict, total=False):
    plan: str
    months: BillingMonths  # 1, 3, 6 or 12
    coupon: str
    type: OrderType
    source: str


class _QuoteOrderBodyRequired(TypedDict):
    plan: PlanName
    months: BillingMonths  # 1, 3, 6 or 12


class QuoteOrderBody(_QuoteOrderBodyRequired, total=False):
    coupon: str


class APIOrderQuoteCoupon(TypedDict):
    code: str
    discount: float


class APIOrderQuote(TypedDict):
    """Price of a plan for a period. Amounts are in BRL."""

    plan: PlanName
    months: BillingMonths
    list_price: float  # monthly list price times the months, before any discount
    period_discount_percent: float
    coupon: APIOrderQuoteCoupon | None
    total: float  # final price
    legacy_price: bool  # the quote uses the price the account already had
    legacy_price_until: str | None  # ISO 8601; None when `legacy_price` is False
    payment_methods: list[Literal["pix", "card"]]


class APIPlanCycle(TypedDict):
    months: BillingMonths
    discount_percent: float


class APIPlanBlobLimits(TypedDict):
    quota_bytes: int
    max_rules: int
    max_custom_domains: int
    image_transformations_per_month: int
    s3_requests_per_10s: int


class APIPlanLimits(TypedDict):
    deploys_per_hour: int
    requests_per_minute: int
    requests_per_day: int
    max_domains: int
    max_domain_ports: int
    manual_backups_per_day: int
    workspace_members: int
    workspace_roles: int
    release_versions: int
    release_retention_days: int
    max_custom_images: int
    web_analytics_history_days: int  # how many days back Web Analytics can be read
    blob: APIPlanBlobLimits


class APIPlanFeatures(TypedDict):
    web_published: bool
    daily_app_backups: bool
    daily_database_backups: bool
    create_backup: bool
    advanced_metrics: bool
    create_workspace: bool
    custom_domain: bool
    custom_subdomain: bool
    file_manager: bool
    database_manager: bool
    auto_deploy: bool
    rollback: bool
    auto_rollback: bool
    zero_downtime: bool
    powered_by_badge: bool
    blob_metadata: bool
    blob_share_password: bool
    blob_unlimited_upload_rate: bool
    blob_no_cache: bool
    blob_short_expiration: bool
    web_analytics_performance: bool  # `GET /v1/apps/:id/analytics/performance`
    web_analytics_requests: bool  # `GET /v1/apps/:id/analytics/requests`


class APIPlan(TypedDict):
    name: PlanName
    family: PlanFamily | None
    legacy: bool  # plan no longer sold
    memory_mb: int
    max_vcpus_per_app: float  # highest vCPU count one application can use
    price: float  # monthly price, in BRL
    payment_methods: list[Literal["pix", "card"]]
    limits: APIPlanLimits
    features: APIPlanFeatures


class APIPlansCatalog(TypedDict):
    """The plans currently for sale and the billing periods with their discounts."""

    cycles: list[APIPlanCycle]
    plans: list[APIPlan]


class APIBillingAddress(TypedDict):
    line1: str
    number: str | None
    line2: str | None
    district: str | None
    city: str
    city_code: str | None
    state: str | None
    postal_code: str | None
    country: str


class BillingTaxIdBody(TypedDict):
    type: Literal["cpf", "cnpj"]
    value: str


class _PutBillingDetailsRequired(TypedDict):
    name: str
    address: APIBillingAddress


class PutBillingDetailsBody(_PutBillingDetailsRequired, total=False):
    phone: str | None  # E.164; None or omitted removes the saved phone
    tax_id: BillingTaxIdBody | None  # None removes the saved document; omitted keeps it


# -- responses -------------------------------------------------------------

ApplicationLanguage = Literal[
    "javascript",
    "typescript",
    "bun",
    "python",
    "static",
    "php",
    "go",
    "ruby",
    "java",
    "rust",
    "deno",
    "dotnet",
    "elixir",
]
ApplicationStatus = Literal["up", "down", "building"]
ApplicationBuildError = Literal[
    "BUILD_FAILED",
    "BUILD_TIMEOUT",
    "BUILD_INTERRUPTED",
    "INSTALL_FAILED",
    "INSTALL_OUT_OF_MEMORY",
    "INSTALL_TIMEOUT",
    "INSTALL_SHIELD_BLOCKED",
    "IMAGE_VOLUME_REFUSED",
    "IMAGE_LABEL_REFUSED",
    "IMAGE_PULL_FAILED",
]
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


class APIApplicationDeploySettings(TypedDict):
    zero_downtime: ApplicationZeroDowntime
    zero_downtime_active: bool
    auto_rollback: bool
    health_check_path: str | None


class APIApplicationDomain(TypedDict):
    id: str
    hostname: str
    apex: bool
    companion_of: str | None
    redirect_to: str | None
    redirect_status: ApplicationDomainRedirectStatus
    path_prefix: str | None
    port: int
    status: ApplicationDomainStatus
    ssl_status: ApplicationDomainSslStatus
    created_at: str


class APIApplicationDomainDnsRecord(TypedDict):
    type: Literal["CNAME", "TXT"]
    name: str
    value: str
    status: Literal["pending", "active"]


class APIApplicationDomainConnect(TypedDict):
    url: str


class _APIApplicationRequired(TypedDict):
    id: str
    cluster: int
    type: int
    name: str
    owner_id: str
    owner_plan: PlanName | None
    language: ApplicationLanguage
    ram: int
    status: ApplicationStatus
    subdomain: str | None
    public_url: str | None
    domains: list[APIApplicationDomain]
    last_snapshot: str | None
    created_at: str
    updated_at: str
    main_file: str
    version: str
    start_command: str | None
    build_command: str | None
    offline_since: str | None
    shield_cooldown: APIApplicationShieldCooldown | None
    deploy: APIApplicationDeploySettings
    auto_restart: bool
    last_build_error: ApplicationBuildError | None
    # Custom Docker image the app runs from; `None` for a regular app.
    custom_image: APIApplicationCustomImage | None


class APIApplication(_APIApplicationRequired, total=False):
    description: str
    github: APIApplicationGithub | None
    # Stack the app belongs to; `None` when it is not in one.
    stack_id: str | None
    # Id of the service of the stack's template this app is; `None` when the user added it.
    stack_service_key: str | None
    # Template the app was created from; `None` (or absent) for an app that did not come from one.
    template: APIApplicationTemplate | None


class APIApplicationCreated(APIApplication, total=False):
    """Response of `apps.create`. `warning` is set when the app was created from the snapshot of an app
    on a custom image and the recorded image version no longer exists: the app uses the current version."""

    warning: SnapshotImageWarning
    # Only when created from `snapshot_id`: the restore job to follow with `snapshot_jobs.get` / `snapshot_jobs.wait`
    # (scope `"applications"`, resource id = this app). The app is created first and its files come back in the
    # background: an app of code that fails to restore is deleted by the API; one on a custom image is kept as is.
    restore_job_id: str


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
    # Set while a restore of this resource is queued or running (follow it on `snapshot_jobs.get`); `None` otherwise.
    restore_job_id: str | None


class APIApplicationStatus(_APIApplicationStatusRequired, total=False):
    installing: bool


class _APIApplicationStatusShortRequired(TypedDict):
    id: str
    cpu: str
    ram: str
    running: bool
    uptime: int | None
    # Set while a restore of this resource is queued or running (follow it on `snapshot_jobs.get`); `None` otherwise.
    restore_job_id: str | None


class APIApplicationStatusShort(_APIApplicationStatusShortRequired, total=False):
    installing: bool


class _APIAppFileUploadResponseRequired(TypedDict):
    app_id: str
    updated_at: str


class APIAppFileUploadResponse(_APIAppFileUploadResponseRequired, total=False):
    removed_directories: list[str]
    # Only for a commit to an app on a custom image: the image build the commit started. `None` otherwise.
    image_build: APIApplicationImageBuild | None
    # Readable summary for the CLI, e.g. that the image is rebuilding.
    message: str


APIMetricEventKind = Literal["restart", "auto_restart", "crash"]
"""`restart` = requested by the user; `auto_restart` = the platform started the resource again after a failure;
`crash` = the resource failed and stayed stopped."""


class APIMetricEvent(TypedDict):
    """An event shown on the metric charts, with its exact time."""

    at: str
    kind: APIMetricEventKind
    out_of_memory: bool
    """`True` when the failure was caused by running out of memory. Always `False` for `restart`."""


class APIApplicationMetric(TypedDict):
    cpu: float
    ram: float
    storage: float
    date: str
    network: list[float]
    events: list[APIMetricEvent]
    """Events between this point's `date` and the next one's (up to now in the last point). An event before the
    first point of the window is listed in the first point. Empty when nothing happened."""


ApplicationRealtimeEventType = Literal["logs", "next_logs", "system", "metrics", "heartbeat"]
"""`SseEvent.event` of `apps.realtime`. `next_logs` is the output of the new version while a zero-downtime deploy
prepares it, in the same format as `logs`; `metrics` only arrives with `metrics=True` and carries
`APIApplicationLiveMetrics` as JSON."""


class APIApplicationLiveMetrics(TypedDict):
    """`data` of a `metrics` event of `apps.realtime`, about every 5 seconds while the app runs. Rates are measured
    between two consecutive readings."""

    at: str
    cpu_percent: float
    """CPU in use as a percentage of the CPU of the app's plan, from 0 to 100."""
    cpu_cores: float
    memory_bytes: int
    """Memory in use, without the reclaimable file cache."""
    memory_limit_bytes: int | None
    net_rx_bps: float
    net_tx_bps: float
    net_rx_bytes: int
    """Bytes received since the app started."""
    net_tx_bytes: int
    """Bytes sent since the app started."""


class APIApplicationEnvironmentManager(TypedDict):
    """The connection of a stack that manages a variable: the platform keeps it up to date."""

    type: Literal["stack_binding"]
    binding_id: str
    # `None` for the address variable of an application that is not in a stack.
    stack_id: str | None


class _APIApplicationEnvironmentRequired(TypedDict):
    id: str
    key: str
    value: str
    note: str | None
    created_at: str


class APIApplicationEnvironment(_APIApplicationEnvironmentRequired, total=False):
    # Set when a stack connection manages the variable. Editing it by hand turns it into an ordinary variable.
    managed_by: APIApplicationEnvironmentManager | None


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


ApplicationReleaseSource = Literal["github", "cli", "upload", "editor", "rollback", "env_change"]
ApplicationReleaseStatus = Literal["deploying", "active", "superseded", "failed", "rolled_back", "expired"]
ApplicationEnvironmentChange = Literal["added", "modified", "removed"]


# Functional syntax: the JSON key `from` is a Python keyword.
APIApplicationReleaseRollback = TypedDict(
    "APIApplicationReleaseRollback", {"available": bool, "expires_at": str | None, "from": str | None}
)


class APIApplicationRelease(TypedDict):
    id: str
    app_id: str
    source: ApplicationReleaseSource
    status: ApplicationReleaseStatus
    message: str | None
    author: str
    github: APIApplicationDeployment | None
    files_changed: int
    rollback: APIApplicationReleaseRollback
    has_log: bool
    build_duration_ms: int | None
    first_started_at: str | None
    created_at: str


class APIApplicationReleasePage(TypedDict):
    data: list[APIApplicationRelease]
    total_count: int
    page: int
    limit: int
    total_pages: int
    has_next_page: bool
    has_previous_page: bool


class APIApplicationReleaseLog(TypedDict):
    content: str | None


class APIApplicationEnvironmentChange(TypedDict):
    key: str
    change: ApplicationEnvironmentChange


class APIApplicationRollbackPreview(TypedDict):
    environment_changes: list[APIApplicationEnvironmentChange]


class APIWebhookUrl(TypedDict):
    url: str


class APIApplicationWebhook(TypedDict):
    """Auto-deploy webhook of an application and the repository it is linked to.
    `branch` is `None` for a link created without one (reacts to `main` or `master`)."""

    webhook_url: str
    repo_owner: str
    repo_name: str
    branch: str | None


class APISubdomainResponse(TypedDict):
    subdomain: str


class APIApplicationWebPublish(TypedDict):
    subdomain: str | None
    domains: list[str]
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


class APIApplicationFileDelete(TypedDict):
    """Answer of `apps.files.delete`: `now` when the space was freed right away, `on_restart` when the file was still
    open and the space returns at the next restart."""

    space_released: Literal["now", "on_restart"]


class APIApplicationFileContent(TypedDict):
    """`data` holds the file bytes in standard base64; `size` is the decoded length."""

    type: Literal["base64"]
    data: str
    size: int
    last_modified: str


class APIRuntimeEntry(TypedDict):
    recommended: str
    latest: str
    specific: list[str]


APIRuntimesResponse = dict[str, APIRuntimeEntry]


class _APIDatabaseRequired(TypedDict):
    id: str
    cluster: int
    type: int
    name: str
    description: str
    owner_id: str
    owner_plan: PlanName | None
    status: DatabaseStatus
    ram: int
    host: str
    port: int
    created_at: str
    updated_at: str
    last_snapshot: str | None
    offline_since: str | None
    legacy_host: bool
    version: str
    """Engine major line, e.g. `"18"` or `"8.0"`; the patch is never exposed. Not limited to the
    catalog: older databases may report a line that is no longer offered for new ones."""


class APIDatabase(_APIDatabaseRequired, total=False):
    # Stack the database belongs to; `None` when it is not in one.
    stack_id: str | None
    # Id of the service of the stack's template this database is; `None` when the user added it.
    stack_service_key: str | None


class _APIDatabaseCreatedRequired(TypedDict):
    password: str
    """The database password. It comes only in this response: store it now; `credentials.password.reset` issues a
    new one."""


class APIDatabaseCreated(APIDatabase, _APIDatabaseCreatedRequired, total=False):
    """Response of `databases.create`. With `snapshot_id`, the data comes back in the background: `restore_job_id`
    is the job to follow (`snapshot_jobs.get` / `snapshot_jobs.wait`, scope `"databases"`). If the restore fails the
    database is kept as it is (it accepts connections from the start); the job's `reason` says why."""

    restore_job_id: str


class APIDatabaseVersionCatalog(TypedDict):
    recommended: str
    available: list[str]


APIDatabaseVersions = dict[str, APIDatabaseVersionCatalog]
"""Catalog keyed by the engine `type` as a string (`"1"`, `"2"`, ...)."""


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
    # Set while a restore of this resource is queued or running (follow it on `snapshot_jobs.get`); `None` otherwise.
    restore_job_id: str | None


class APIDatabaseStatusShort(TypedDict):
    id: str
    cpu: str
    ram: str
    storage: str
    running: bool
    # Set while a restore of this resource is queued or running (follow it on `snapshot_jobs.get`); `None` otherwise.
    restore_job_id: str | None


class APIDatabaseMetrics(TypedDict):
    cpu: float
    ram: float
    storage: float
    date: str
    network: list[float]
    events: list[APIMetricEvent]
    """Same as `APIApplicationMetric.events`."""


class APIRestartRequired(TypedDict):
    """Answer of a change that alters variables or certificates of applications in a stack: an app reads them
    only when it starts, so the restart is yours to ask for."""

    restart_required: bool
    apps_to_restart: list[str]


class APIDatabasePasswordReset(APIRestartRequired):
    password: str


class APIDatabaseCertificate(TypedDict):
    crt: str
    key: str
    pem: str


class APIDatabaseClientVariableWithOldHost(TypedDict):
    app_id: str
    key: str


class APIDatabaseCertificateReset(APIDatabaseCertificate, APIRestartRequired):
    """New certificate after `databases.credentials.certificate.reset`, with the apps that must restart to read it,
    the `host` it was issued for and the app variables that still hold the old address (empty when the address does
    not change)."""

    host: str
    client_variables_with_old_host: list[APIDatabaseClientVariableWithOldHost]


class _APIResourceSnapshotRequired(TypedDict):
    id: str
    resource_id: str
    resource_type: int | None
    size: str
    date: str
    resource_name: str | None


class APIResourceSnapshot(_APIResourceSnapshotRequired, total=False):
    # True for a snapshot of an app of a closed template: it cannot be downloaded, only restores into an app of the
    # same template (anything else fails with `TEMPLATE_CLOSED`).
    closed: bool
    # What took the snapshot. Absent on snapshots that predate this field.
    origin: SnapshotOrigin
    # Applications only: files that kept changing while the snapshot was read. 0 or absent: none.
    changed_files: int


class APIGroupedResourceSnapshots(TypedDict):
    resource_id: str
    resource_name: str | None
    type: ResourceType
    resource_type: int | None
    snapshots: list[APIResourceSnapshot]


class _APIDatabaseResetRequired(TypedDict):
    status: Literal["success"]


class APIDatabaseReset(_APIDatabaseResetRequired):
    """What `databases.reset` returns: `{"status": "success"}`."""


class _APISnapshotRestoreAcceptedRequired(TypedDict):
    job_id: str


class APISnapshotRestoreAccepted(_APISnapshotRestoreAcceptedRequired, total=False):
    """What `snapshots.restore` returns: the restore was accepted (HTTP 202) and runs as a job, so the resource is
    not restored yet. Follow `job_id` with `snapshot_jobs.get` or `snapshot_jobs.wait`."""

    # Set when `restore_image_version` was asked but the recorded image version is gone: only the data is restored.
    warning: SnapshotImageWarning


# What took a snapshot: you (`manual`) or the plan's daily backup (`automatic`).
SnapshotOrigin = Literal["manual", "automatic"]
SnapshotJobKind = Literal["snapshot", "restore"]
SnapshotJobStatus = Literal["queued", "running", "ready", "skipped", "failed"]
SnapshotJobPhase = Literal["preparing", "copying", "finishing"]


class _APISnapshotJobRequired(TypedDict):
    id: str
    kind: SnapshotJobKind
    # The resource the job acts on: the one being backed up, or the target of a restore.
    resource_id: str
    status: SnapshotJobStatus
    created_at: str


class _APISnapshotJobProgressRequired(TypedDict):
    phase: SnapshotJobPhase


class APISnapshotJobProgress(_APISnapshotJobProgressRequired, total=False):
    """Progress of a `running` job. `percent` (0-100) is absent when the total size is not known (database
    snapshots) and `eta_seconds` until there is a stable rate."""

    percent: float
    done_bytes: int
    total_bytes: int
    eta_seconds: float


class APISnapshotJob(_APISnapshotJobRequired, total=False):
    """A snapshot or restore job of a resource."""

    # Error code of a `failed` (or `skipped`) job.
    reason: str
    # The same `details` the error `reason` would carry on a direct response, when it has any. Only with `reason`.
    details: APISnapshotTooLargeDetails | APISnapshotExceedsStorageDetails
    # Snapshot jobs: the snapshot the job produced; a `ready` snapshot job always has it. Restore jobs: the snapshot
    # being restored, from the start.
    snapshot_id: str
    # Snapshot jobs only: what asked for the snapshot. Absent on restore jobs.
    origin: SnapshotOrigin
    started_at: str
    finished_at: str
    # Only while `running`; absent when queued, once the job ends, or when it is not known.
    progress: APISnapshotJobProgress


class APISnapshotTooLargeDetails(TypedDict):
    """`details` of `SNAPSHOT_TOO_LARGE` (413): the largest content, in bytes, a snapshot of the resource can have."""

    max_bytes: int


class APIRestoreCooldownDetails(TypedDict):
    """`details` of `RESTORE_COOLDOWN` (429), also sent by a release rollback: seconds until a restore of the resource
    is accepted again (`RateLimitError.retry_after` and the `Retry-After` header carry the same value)."""

    retry_after: int


class APIOperationInProgressDetails(TypedDict, total=False):
    """`details` of `OPERATION_IN_PROGRESS` (409) when creating a snapshot: a manual snapshot of the same resource is
    already queued or running and `job_id` is its job (`snapshot_jobs.wait`). Absent for any other cause."""

    job_id: str


class APISnapshotCreateAccepted(TypedDict):
    """What `snapshots.create` returns on the 202 answer (the snapshot is still being taken): follow `job_id` with
    `snapshot_jobs.wait`; the snapshot shows up in `snapshots.list` when it is ready."""

    job_id: str


class _APISnapshotExceedsStorageDetailsRequired(TypedDict):
    required_bytes: int
    available_bytes: int


class APISnapshotExceedsStorageDetails(_APISnapshotExceedsStorageDetailsRequired, total=False):
    """`details` of `SNAPSHOT_EXCEEDS_STORAGE` (400): the snapshot does not fit in the target."""

    # Databases only: the smallest memory size, in MB, whose storage has room for the snapshot.
    required_ram_mb: int


class APIUser(TypedDict):
    id: str
    name: str
    email: str
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
    name: PlanName
    expires_at: str
    duration: int
    memory: APIUserPlanMemory


class APIWorkspaceResourceRef(TypedDict):
    resource_type: Literal["application", "database", "image", "stack"]
    resource_id: str


class APIWorkspaceFolderItem(APIWorkspaceResourceRef):
    position: int


class _APIWorkspaceResourceFolderRequired(TypedDict):
    id: str
    name: str
    color: str
    position: int
    resources: list[APIWorkspaceFolderItem]
    created_at: str
    updated_at: str


class APIWorkspaceResourceFolder(_APIWorkspaceResourceFolderRequired, total=False):
    # Free-text notes of the folder; `None` when it has none.
    notes: str | None
    # Position of the folder on the Flow canvas; `None` until it is placed.
    flow_layout: WorkspaceFolderFlowLayout | None


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
    plan: APIUserPlan | None
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
    owner_plan: PlanName | None
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
    allowed_payment_methods: list[OrderProvider]


class APIBillingTaxId(TypedDict):
    type: Literal["cpf", "cnpj"]
    masked: str


class APIBillingDetails(TypedDict):
    name: str | None
    address: APIBillingAddress | None
    phone: str | None
    tax_id: APIBillingTaxId | None
    complete: bool


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
    allowed_payment_methods: list[OrderProvider]
    expires_at: str | None


class APIOrderListItem(TypedDict):
    id: str
    status: str
    price: float
    provider: str
    type: str
    related_to: APIOrderListItemRelatedTo
    created_at: str
    paid_at: str | None
    has_receipt: bool


class APIPixQrCode(TypedDict):
    copy: str | None
    base64: str | None


class APIPixPaymentResponse(TypedDict):
    transaction_amount: float | str
    external_reference: str | None
    txid: str
    qrcode: APIPixQrCode
    expires_at: str | None


class APIRedeemPlan(TypedDict):
    name: str
    duration: int


class APIRedeemResponse(TypedDict):
    plan: APIRedeemPlan


# -- Blob Storage ----------------------------------------------------------------------

BlobVisibility = Literal["public", "private"]
BlobContentDisposition = Literal["inline", "attachment"]
BlobUploadMode = Literal["single", "multipart"]
BlobUploadStatus = Literal["pending", "completed", "aborted", "expired"]
BlobCustomDomainStatus = Literal["pending", "active", "failed", "suspended"]


class APIBlobObject(TypedDict):
    id: str
    path: str
    size: int
    content_type: str
    etag: str
    sha256: str | None
    visibility: BlobVisibility
    url: str | None
    cache_control: str | None
    content_disposition: BlobContentDisposition
    filename: str | None
    metadata: dict[str, str]
    expires_at: str | None
    created_at: str
    updated_at: str


class APIBlobObjectList(TypedDict):
    objects: list[APIBlobObject]
    folders: list[str]
    cursor: str | None


class _APIBlobUploadOptional(TypedDict, total=False):
    url: str
    part_size: int
    part_count: int
    uploaded_parts: list[int]


class APIBlobUpload(_APIBlobUploadOptional):
    id: str
    path: str
    mode: BlobUploadMode
    status: BlobUploadStatus
    size: int
    expires_at: str
    headers: dict[str, str]
    created_at: str


class APIBlobUploadPart(TypedDict):
    part_number: int
    url: str
    size: int
    headers: dict[str, str]


class APIBlobLimits(TypedDict):
    max_simple_upload_bytes: int
    max_single_put_bytes: int
    max_object_bytes: int
    min_part_bytes: int
    max_part_bytes: int
    max_parts: int
    max_open_uploads: int
    uploads_per_second: int | None
    max_rules: int
    max_custom_domains: int
    metadata_enabled: bool
    share_password_enabled: bool
    no_cache_enabled: bool
    min_expiration_seconds: int
    image_transformations_per_month: int


class APIBlobStats(TypedDict):
    objects: int
    used_bytes: int
    quota_bytes: int
    over_quota_bytes: int
    estimated_overage_cents: int
    month_average_bytes: int
    image_transformations_used: int
    public_base_url: str
    limits: APIBlobLimits


class _APIBlobBatchResultOptional(TypedDict, total=False):
    code: str
    object: APIBlobObject


class APIBlobBatchResult(_APIBlobBatchResultOptional):
    id: str
    ok: bool


class APIBlobDeleteResult(TypedDict):
    deleted: list[str]
    not_found: list[str]
    remaining: bool


class APIBlobDownload(TypedDict):
    url: str
    expires_at: str


class APIBlobUploadToken(TypedDict):
    token: str
    expires_at: str
    max_uses: int


class APIBlobShare(TypedDict):
    id: str
    object_id: str
    url: str
    expires_at: str
    max_downloads: int | None
    remaining_downloads: int | None
    has_password: bool
    object_is_public: bool
    created_at: str


class BlobRuleInput(TypedDict, total=False):
    """Fields of a folder rule (`rules.put`); `rules.set` also needs `prefix` on each item."""

    prefix: str
    visibility: BlobVisibility
    expire_seconds: int
    max_size: int
    extensions: list[str]
    cache_control: str
    delete_after_days: int


class APIBlobRule(BlobRuleInput):
    active_from: str
    created_at: str


class APIBlobRules(TypedDict):
    rules: list[APIBlobRule]
    etag: str


class _APIBlobS3Access(TypedDict):
    read: bool
    write: bool


class APIBlobS3Credentials(TypedDict):
    access_key_id: str
    secret_access_key: str
    endpoint: str
    region: Literal["auto"]
    buckets: list[str]
    access: _APIBlobS3Access


class APIBlobCustomDomainVerification(TypedDict):
    type: Literal["txt"]
    name: str
    value: str


class _APIBlobCustomDomainRequired(TypedDict):
    id: str
    hostname: str
    status: BlobCustomDomainStatus
    ssl_status: str
    cname_target: str
    prefix: str | None
    # true: the domain serves .html/.htm/.xhtml/.svg/.xml in the browser (sandboxed); false: always downloads.
    web_content: bool
    created_at: str


class APIBlobCustomDomain(_APIBlobCustomDomainRequired, total=False):
    # Only while the domain is not active: the TXT record that proves ownership.
    verification: APIBlobCustomDomainVerification | None


# -- Custom Docker images: `images.*` and `apps.create_from_image` ---------------------------

CustomImageStatus = Literal["building", "success", "failed"]
CustomImageBuildSource = Literal["upload", "commit", "github"]
CustomImageOwner = Literal["account", "system"]
DockerfileIssueCode = Literal[
    "missing_dockerfile",
    "syntax_frontend",
    "run_security_insecure",
    "run_network_host",
    "mount_ssh",
    "mount_secret",
    "workdir_app",
    "env_file_in_context",
    "copy_env_file",
    "volume_outside_app",
    "volume_refused",
]


class DockerfileIssue(TypedDict):
    """Refusals block the build; warnings do not. `line` is `None` when no line applies."""

    code: DockerfileIssueCode
    line: int | None


class APIDockerfileCheck(TypedDict):
    refusals: list[DockerfileIssue]
    warnings: list[DockerfileIssue]
    suggested_port: int


class APICustomImageApp(TypedDict):
    id: str
    name: str
    version_id: str | None
    outdated: bool


class APIApplicationCustomImage(APICustomImageApp):
    """`APIApplication.custom_image`: the image the app runs from and the port it listens on."""

    image_id: str
    port: int | None


class APICustomImageGithub(TypedDict):
    repository: str
    branch: str


CustomImageKind = Literal["own", "template_copy"]


class APICustomImageOrigin(TypedDict):
    """Readable origin of an image that came from a template."""

    template_id: str
    template_name: APITemplateI18nText
    # Author as shown to you; `None` for a template of the platform.
    author_display: str | None


class _APICustomImageRequired(TypedDict):
    id: str
    name: str
    # Free-text description, up to 128 characters; None when the image has none.
    description: str | None
    owner: CustomImageOwner
    status: CustomImageStatus
    error: str | None
    digest: str | None
    uncompressed_bytes: int | None
    layer_count: int | None
    # Port suggested for a new app on this image (first EXPOSE, or 80); None for images created before the field.
    suggested_port: int | None
    apps: list[APICustomImageApp]
    github: APICustomImageGithub | None
    current_version_id: str | None
    created_at: str
    updated_at: str


class APICustomImage(_APICustomImageRequired, total=False):
    # `"own"` (built from your own context) or `"template_copy"` (the slot an image of a template takes in your
    # account: it cannot be rebuilt or edited, `IMAGE_TEMPLATE_ONLY`). Absent in older payloads, where it means `"own"`.
    kind: CustomImageKind
    # Template the image came from when `kind` is `"template_copy"`; `None` otherwise.
    origin: APICustomImageOrigin | None


class APICustomImageVersion(TypedDict):
    id: str
    digest: str
    source: CustomImageBuildSource
    message: str | None
    created_at: str
    in_use: bool


class APICustomImageContext(TypedDict):
    url: str


class APICustomImageDeleteResult(TypedDict):
    deleted_apps: list[str]


class _CreateCustomImageRequired(TypedDict):
    name: str


class CreateCustomImageBody(_CreateCustomImageRequired, total=False):
    """`POST /v1/images` fields. Exactly one source: a `file` passed to `images.create`, or
    `github_repository` (`owner/name`). `github_branch` is optional; without it the repository's default
    branch is used. A repository in your GitHub App installations is linked (each push to the branch
    rebuilds the image); a public repository outside them is built once, with no link.
    `description` is optional free text, up to 128 characters (an empty value means none)."""

    description: str
    github_repository: str
    github_branch: str
    workspace_id: str


class _CustomImageGithubRequired(TypedDict):
    repository: str


class UpdateCustomImageBody(TypedDict, total=False):
    """`PATCH /v1/images/:image_id` fields; send only what changes (at least one). `name` is 1 to 50
    characters, unique among your images. `description` is up to 128 characters; `None` or an empty
    string removes it."""

    name: str
    description: str | None


class CustomImageGithubBody(_CustomImageGithubRequired, total=False):
    """`PUT /v1/images/:image_id/github` fields. `branch` is optional: without it the repository's
    default branch is used. The repository must be in one of your GitHub App installations."""

    branch: str


class CheckDockerfileBody(TypedDict):
    dockerfile: str
    files: list[str]


class APIApplicationImageBuild(TypedDict):
    """The image build started by a commit to an app on a custom image (`apps.files.upload`)."""

    image_id: str
    build_id: str


# Warning of a snapshot restore or of a create from a snapshot: the image version the snapshot recorded was
# removed by retention, so the app stays on the image's current version.
SnapshotImageWarning = Literal["IMAGE_VERSION_NOT_FOUND"]


class _CreateAppFromImageRequired(TypedDict):
    image_id: str
    name: str
    memory: int
    web: bool


class CreateAppFromImageBody(_CreateAppFromImageRequired, total=False):
    """`POST /v1/apps/image`. `subdomain` and `port` apply only with `web: True`."""

    description: str
    subdomain: str
    port: int
    envs: list[EnvEntry]
    workspace_id: str
    auto_restart: bool


# -- Templates and stacks: `templates.*`, `stacks.*` ----------------------------------------------

TemplateOrigin = Literal["vertra", "community", "private"]
TemplateVisibility = Literal["public", "beta", "hidden", "deprecated"]
TemplateCategory = Literal[
    "automation", "ai-agents", "bots", "apis", "cms", "monitoring", "starters", "databases", "other"
]
TemplateSourceType = Literal["code", "image"]
TemplateWebMode = Literal["required", "optional", "none"]
TemplateInputType = Literal["text", "secret", "select", "boolean", "number", "url", "email"]
TemplateDatabaseEngine = Literal["postgres", "mysql", "mongodb", "redis"]
TemplateBlobVisibility = Literal["private", "public"]
TemplateShareLinkMode = Literal["use", "full_copy"]
TemplateDeployStatus = Literal["queued", "running", "undoing", "succeeded", "failed"]
TemplateDeployKind = Literal["deploy", "update"]
TemplateDeployStep = Literal[
    "validate",
    "snapshot",
    "network",
    "databases",
    "blob",
    "images",
    "apps",
    "variables",
    "certificates",
    "start",
    "healthcheck",
    "outputs",
    "rollback",
]
TemplateDeployStepStatus = Literal["pending", "running", "done", "skipped", "failed"]
TemplateReportReason = Literal["malware", "scam", "copyright", "leaked_secret", "other"]
TemplateFitReason = Literal[
    "no_plan",
    "ram",
    "web_publish",
    "image_plan",
    "image_slots",
    "private_network",
    "blob_plan",
    "min_plan",
    "max_apps",
    "max_databases",
    "deploys_per_hour",
]
TemplateUpdateBlockReason = Literal[
    "no_new_version",
    "detached",
    "template_removed",
    "link_revoked",
    "ram",
    "plan",
    "image_slots",
    "app_building",
    "deploy_in_progress",
]
TemplateValidationCode = Literal[
    "invalid_type",
    "required",
    "unknown_field",
    "invalid_slug",
    "invalid_version",
    "invalid_category",
    "invalid_text",
    "invalid_ram",
    "invalid_plan",
    "unknown_placeholder",
    "unknown_service",
    "unknown_input",
    "invalid_when",
    "invalid_option",
    "invalid_source",
    "invalid_permissions",
    "forbidden_env",
    "forbidden_in_public",
    "secret_in_manifest",
    "invalid_deploy",
    "invalid_connection",
    "duplicate_id",
    "too_many_services",
]
TemplateEnvReviewMode = Literal["question", "keep", "generate", "hidden", "omit"]
TemplateDetachConfirmationAction = Literal["files.write", "deploy.code", "deploy.github", "commit"]
TemplateListSort = Literal["recommended", "popular", "newest", "name"]
TemplateInputValue = str | int | float | bool

# Limits of the manifest texts.
TEMPLATE_NAME_MAX_LENGTH = 50
TEMPLATE_DESCRIPTION_MAX_LENGTH = 128

_APITemplateI18nTextRequired = TypedDict("_APITemplateI18nTextRequired", {"pt-br": str})


class APITemplateI18nText(_APITemplateI18nTextRequired, total=False):
    """Text in up to three languages; `pt-br` is required (the fallback)."""

    en: str
    es: str


class APITemplateEffectivePermissions(TypedDict):
    code_view: bool
    code_edit: bool
    ram_change: bool
    ram_below_min: bool
    ram_above_max: bool
    env_add: bool
    commands_edit: bool
    terminal: bool
    save_as_template: bool
    detach: bool


class _APITemplateOriginRequired(TypedDict):
    template_id: str
    slug: str
    name: APITemplateI18nText
    icon_url: str | None
    origin: TemplateOrigin
    version_id: str
    version: str
    closed: bool
    detached: bool
    update_available: bool
    latest_version: str | None
    removed: bool
    via_share_link: bool


class APITemplateOrigin(_APITemplateOriginRequired):
    """Where an app or a stack came from: the template, its version and whether it still follows it."""


class _APIApplicationTemplateOptional(TypedDict, total=False):
    # Deploy settings the template locks for this app ("zero_downtime", "auto_rollback"): updating the config to
    # another value fails with TEMPLATE_SETTING_LOCKED. Empty once the app is detached.
    locked_deploy_settings: list[Literal["zero_downtime", "auto_rollback"]]


class APIApplicationTemplate(APITemplateOrigin, _APIApplicationTemplateOptional):
    """`APIApplication.template`: the origin plus the service this app is and what the user can do with it."""

    service_id: str | None
    permissions: APITemplateEffectivePermissions


# -- manifest (what a private template is made of; the public catalog uses the same shape)


class APITemplateLinks(TypedDict, total=False):
    website: str
    docs: str
    source: str
    license: str


class _APITemplateRamRequired(TypedDict):
    min: int
    recommended: int


class APITemplateRam(_APITemplateRamRequired, total=False):
    max: int


class APITemplateWhen(TypedDict):
    input: str
    equals: str | int | float | bool


class APITemplateInputValidation(TypedDict, total=False):
    regex: str
    min: float
    max: float
    min_length: int
    max_length: int


class APITemplateOptionSets(TypedDict, total=False):
    services: dict[str, Literal["on", "off"]]
    env: dict[str, dict[str, str]]
    ram_extra: dict[str, int]


class _APITemplateInputOptionRequired(TypedDict):
    value: str


class APITemplateInputOption(_APITemplateInputOptionRequired, total=False):
    label: APITemplateI18nText
    sets: APITemplateOptionSets


class _APITemplateInputRequired(TypedDict):
    id: str
    type: TemplateInputType
    label: APITemplateI18nText


class APITemplateInput(_APITemplateInputRequired, total=False):
    help: APITemplateI18nText
    required: bool
    default: TemplateInputValue
    validation: APITemplateInputValidation
    generate: str
    editable: bool
    when: APITemplateWhen
    options: list[APITemplateInputOption]


class APITemplatePermissions(TypedDict, total=False):
    """What the people who use the template may do; each group is optional."""

    code: dict[str, bool]
    ram: dict[str, bool]
    env: dict[str, bool]
    commands: dict[str, bool]
    version: dict[str, bool]
    share: dict[str, bool]


class APITemplateDeploySettings(TypedDict, total=False):
    zero_downtime: dict[str, Any]
    auto_rollback: dict[str, Any]
    rollback: dict[str, Any]


class _APITemplateSourceRequired(TypedDict):
    type: TemplateSourceType


class APITemplateSource(_APITemplateSourceRequired, total=False):
    image: str
    path: str
    context: str


class _APITemplateHealthcheckRequired(TypedDict):
    timeout: int


class APITemplateHealthcheck(_APITemplateHealthcheckRequired, total=False):
    path: str


class _APITemplateAppServiceRequired(TypedDict):
    source: APITemplateSource
    ram: APITemplateRam
    web: TemplateWebMode


class APITemplateAppService(_APITemplateAppServiceRequired, total=False):
    language: ApplicationLanguage
    runtime_version: str
    main: str
    build: str
    start: str
    port: int
    env: dict[str, str]
    env_hidden: list[str]
    healthcheck: APITemplateHealthcheck
    deploy: APITemplateDeploySettings
    connections: dict[str, dict[str, Literal["required"]]]


class _APITemplateDatabaseServiceRequired(TypedDict):
    database: TemplateDatabaseEngine
    ram: APITemplateRam


class APITemplateDatabaseService(_APITemplateDatabaseServiceRequired, total=False):
    version: str
    when: APITemplateWhen


class _APITemplateBlobServiceRequired(TypedDict):
    blob: dict[str, TemplateBlobVisibility]


class APITemplateBlobService(_APITemplateBlobServiceRequired, total=False):
    when: APITemplateWhen


APITemplateService = APITemplateAppService | APITemplateDatabaseService | APITemplateBlobService


class _APITemplateOutputRequired(TypedDict):
    label: APITemplateI18nText
    value: str | APITemplateI18nText


class APITemplateOutput(_APITemplateOutputRequired, total=False):
    secret: bool
    once: bool


class _APITemplateManifestRequired(TypedDict):
    id: str
    version: str
    name: APITemplateI18nText
    description: APITemplateI18nText
    category: TemplateCategory
    services: dict[str, APITemplateService]


class APITemplateManifest(_APITemplateManifestRequired, total=False):
    tags: list[str]
    icon: str
    links: APITemplateLinks
    landing: str
    min_plan: str
    inputs: list[APITemplateInput]
    permissions: APITemplatePermissions
    outputs: list[APITemplateOutput]
    secrets: list[str]
    byok: bool


# -- catalog


class APITemplateServiceSummary(TypedDict):
    id: str
    kind: Literal["app", "database", "blob"]
    source_type: TemplateSourceType | None
    database: TemplateDatabaseEngine | None
    blob_visibility: TemplateBlobVisibility | None
    ram: APITemplateRam
    web: TemplateWebMode | None
    conditional: bool


class APITemplateOwner(TypedDict):
    user_id: str
    workspace_id: str | None


class APITemplateVersionSummary(TypedDict):
    id: str
    version: str
    security: bool
    created_at: str


class _APITemplateFitIssueRequired(TypedDict):
    reason: TemplateFitReason


class APITemplateFitIssue(_APITemplateFitIssueRequired, total=False):
    required: int | str
    available: int | str


class APITemplateAccountContext(TypedDict):
    """How the template fits the account of the caller (only with authentication)."""

    fits: bool
    reasons: list[APITemplateFitIssue]
    required_ram: int
    free_ram: int
    needs_image_slot: bool
    image_slots_free: int
    in_use: bool
    in_use_count: int


class APITemplateGithubLink(TypedDict):
    repository: str
    branch: str


class _APITemplateRequired(TypedDict):
    id: str
    slug: str
    origin: TemplateOrigin
    visibility: TemplateVisibility
    name: APITemplateI18nText
    description: APITemplateI18nText
    category: TemplateCategory
    tags: list[str]
    icon_url: str | None
    author_display: str | None
    links: APITemplateLinks
    landing: str | None
    featured: bool
    current_version: APITemplateVersionSummary
    services: list[APITemplateServiceSummary]
    creates_stack: bool
    ram_min_total: int
    byok: bool
    required_plan: str
    code_view: bool
    uses_count: int | None
    owner: APITemplateOwner | None
    github: APITemplateGithubLink | None
    created_at: str
    updated_at: str


class APITemplate(_APITemplateRequired, total=False):
    # Only for an authenticated caller.
    account: APITemplateAccountContext


class APITemplateDetail(APITemplate):
    inputs: list[APITemplateInput]
    permissions: APITemplateEffectivePermissions
    outputs: list[APITemplateOutput]
    readme: APITemplateI18nText | None
    changelog: APITemplateI18nText | None


class APITemplateVersion(APITemplateVersionSummary):
    changelog: APITemplateI18nText | None
    manifest: APITemplateManifest | None


class APITemplateCategoryCount(TypedDict):
    category: TemplateCategory
    count: int


class APITemplatePage(TypedDict):
    """One page of `templates.list`."""

    data: list[APITemplate]
    total_count: int
    page: int
    limit: int
    total_pages: int
    has_next_page: bool
    has_previous_page: bool


class APITemplateValidationIssue(TypedDict):
    path: str
    code: TemplateValidationCode
    message: str


class APITemplateValidation(TypedDict):
    valid: bool
    issues: list[APITemplateValidationIssue]
    required_plan: str | None
    ram_min_total: int | None
    services: list[APITemplateServiceSummary]


# -- deploy


class _APITemplateDeployStepStateRequired(TypedDict):
    step: TemplateDeployStep
    status: TemplateDeployStepStatus
    started_at: str | None
    finished_at: str | None


class APITemplateDeployStepState(_APITemplateDeployStepStateRequired, total=False):
    # Only on the `snapshot` and `rollback` steps of an update: one job per app or database (a snapshot job on
    # `snapshot`, a restore job on `rollback`), present once the step has queued them. Follow each with
    # `snapshot_jobs` using `resource_id`.
    jobs: list[APIStackSnapshotJob]


class _APITemplateDeployErrorRequired(TypedDict):
    code: str
    message: str
    step: TemplateDeployStep | None


class APITemplateDeployError(_APITemplateDeployErrorRequired, total=False):
    details: dict[str, Any]


class APITemplateDeployResource(TypedDict):
    resource_type: Literal["application", "database", "image", "stack"]
    resource_id: str
    service_id: str | None
    name: str


class APITemplateDeployOutput(TypedDict):
    """An output of the template. `once` outputs come back on the first read of a finished job only."""

    label: APITemplateI18nText
    value: str | APITemplateI18nText | None
    secret: bool
    once: bool


class APITemplateDeployDatabasePassword(TypedDict):
    database_id: str
    service_id: str
    password: str


class APITemplateDeploy(TypedDict):
    id: str
    kind: TemplateDeployKind
    template_id: str
    version_id: str
    version: str
    status: TemplateDeployStatus
    current_step: TemplateDeployStep | None
    steps: list[APITemplateDeployStepState]
    error: APITemplateDeployError | None
    resources: list[APITemplateDeployResource]
    stack_id: str | None
    application_id: str | None
    outputs: list[APITemplateDeployOutput]
    database_passwords: list[APITemplateDeployDatabasePassword]
    created_at: str
    updated_at: str
    finished_at: str | None


class APITemplateDeployEvent(TypedDict):
    """One progress event of `templates.deploys.events`. Outputs are never on the stream: read them with `get`."""

    deploy_id: str
    status: TemplateDeployStatus
    current_step: TemplateDeployStep | None
    steps: list[APITemplateDeployStepState]
    error: APITemplateDeployError | None


class TemplateDeployServiceOptions(TypedDict, total=False):
    name: str
    ram: int
    subdomain: str


class _TemplateDeployBodyRequired(TypedDict):
    name: str


class TemplateDeployBody(_TemplateDeployBodyRequired, total=False):
    """`POST /v1/templates/:id/deploy`. The idempotency key is not a field: pass `idempotency_key=` to `deploy`."""

    description: str
    # Only valid when the template lets you choose the version; default: the latest.
    version: str
    inputs: dict[str, TemplateInputValue]
    services: dict[str, TemplateDeployServiceOptions]
    network_mode: StackNetworkMode
    workspace_id: str
    folder_id: str


class _TemplateShareDeployBodyRequired(TypedDict):
    name: str


class TemplateShareDeployBody(_TemplateShareDeployBodyRequired, total=False):
    """`POST /v1/share/templates/:token/deploy`: as `TemplateDeployBody`, without a version."""

    description: str
    inputs: dict[str, TemplateInputValue]
    services: dict[str, TemplateDeployServiceOptions]
    network_mode: StackNetworkMode
    workspace_id: str
    folder_id: str


# -- updates and detaching


class APITemplateUpdateBlocked(TypedDict, total=False):
    reason: TemplateUpdateBlockReason
    details: dict[str, Any]


class APITemplateRamChange(TypedDict):
    service_id: str
    current: int
    required_min: int


class APITemplateUpdateInfo(TypedDict):
    update_available: bool
    current_version: str
    latest_version: str | None
    security: bool
    changelog: APITemplateI18nText | None
    new_inputs: list[APITemplateInput]
    added_services: list[APITemplateServiceSummary]
    removed_services: list[str]
    ram_changes: list[APITemplateRamChange]
    free_ram: int
    opens_permissions: bool
    rollback_with_data: bool
    blocked: APITemplateUpdateBlocked | None


class TemplateUpdateBody(TypedDict, total=False):
    inputs: dict[str, TemplateInputValue]
    ram: dict[str, int]


# -- private templates


class _TemplateCreateBodyRequired(TypedDict):
    manifest: APITemplateManifest | dict[str, Any]


class TemplateCreateBody(_TemplateCreateBodyRequired, total=False):
    """`POST /v1/templates` (multipart). The ZIP of each service that runs code goes in `sources`, by service id."""

    changelog: APITemplateI18nText
    workspace_id: str


class _TemplateVersionBodyRequired(TypedDict):
    manifest: APITemplateManifest | dict[str, Any]


class TemplateVersionBody(_TemplateVersionBodyRequired, total=False):
    changelog: APITemplateI18nText


class _TemplateEnvReviewRequired(TypedDict):
    key: str
    mode: TemplateEnvReviewMode


class TemplateEnvReview(_TemplateEnvReviewRequired, total=False):
    label: APITemplateI18nText
    help: APITemplateI18nText
    generate: str


class _TemplateFromMemberRequired(TypedDict):
    resource_id: str
    service_id: str


class TemplateFromMember(_TemplateFromMemberRequired, total=False):
    env: list[TemplateEnvReview]
    paths: list[str]
    ram: APITemplateRam


class _TemplateFromAppBodyRequired(TypedDict):
    id: str
    name: APITemplateI18nText
    description: APITemplateI18nText
    category: TemplateCategory
    member: TemplateFromMember


class TemplateFromAppBody(_TemplateFromAppBodyRequired, total=False):
    tags: list[str]
    version: str
    permissions: APITemplatePermissions
    workspace_id: str


class _TemplateFromStackBodyRequired(TypedDict):
    id: str
    name: APITemplateI18nText
    description: APITemplateI18nText
    category: TemplateCategory
    members: list[TemplateFromMember]


class TemplateFromStackBody(_TemplateFromStackBodyRequired, total=False):
    tags: list[str]
    version: str
    permissions: APITemplatePermissions
    workspace_id: str


class APITemplateDraftEnv(TypedDict):
    key: str
    looks_secret: bool
    suggested_mode: TemplateEnvReviewMode


class APITemplateDraftPath(TypedDict):
    path: str
    type: Literal["file", "directory"]
    selected: bool
    reason: Literal["env_file", "platform_folder", "dependencies", "database_file", "uploads"] | None


class APITemplateDraftMember(TypedDict):
    resource_id: str
    resource_type: Literal["application", "database"]
    name: str
    ram: APITemplateRam
    env: list[APITemplateDraftEnv]
    paths: list[APITemplateDraftPath]


class APITemplateDraft(TypedDict):
    """What an app or stack would put in a template: review the variables and paths before `from_app`/`from_stack`."""

    members: list[APITemplateDraftMember]


class TemplateUpdateDetailsBody(TypedDict, total=False):
    name: APITemplateI18nText
    description: APITemplateI18nText
    category: TemplateCategory
    tags: list[str]


class _TemplateGithubLinkBodyRequired(TypedDict):
    repository: str


class TemplateGithubLinkBody(_TemplateGithubLinkBodyRequired, total=False):
    branch: str


class _TemplateReportBodyRequired(TypedDict):
    reason: TemplateReportReason


class TemplateReportBody(_TemplateReportBodyRequired, total=False):
    details: str


# -- share links


class TemplateShareLinkCreateBody(TypedDict, total=False):
    mode: TemplateShareLinkMode
    max_uses: int
    expires_in_days: int


class APITemplateShareLink(TypedDict):
    id: str
    template_id: str
    mode: TemplateShareLinkMode
    last4: str
    uses: int
    max_uses: int | None
    expires_at: str | None
    revoked_at: str | None
    created_at: str


class APITemplateShareLinkCreated(APITemplateShareLink):
    """The token appears here only: it is not shown again."""

    token: str


class _APITemplateSharePreviewRequired(TypedDict):
    mode: TemplateShareLinkMode
    name: APITemplateI18nText
    description: APITemplateI18nText
    category: TemplateCategory
    icon_url: str | None
    author_display: str | None
    version: str
    services: list[APITemplateServiceSummary]
    creates_stack: bool
    ram_min_total: int
    required_plan: str
    image_slots_needed: int
    verified: Literal[False]
    code_view: bool
    byok: bool
    inputs: list[APITemplateInput]
    permissions: APITemplateEffectivePermissions


class APITemplateSharePreview(_APITemplateSharePreviewRequired, total=False):
    account: APITemplateAccountContext


class TemplateShareCopyBody(TypedDict, total=False):
    workspace_id: str


# -- stacks

StackNetworkMode = Literal["public", "private"]
StackMemberType = Literal["application", "database", "blob"]
StackBlobDisposition = Literal["keep", "delete"]
StackBindingRemoval = Literal["keep_connection", "remove_variables"]
StackDeleteMode = Literal["dissolve", "delete_all"]
StackSnapshotReason = Literal["manual", "update"]
StackBindingValue = Literal[
    "url",
    "host",
    "port",
    "user",
    "password",
    "database",
    "ssl.ca_path",
    "ssl.cert_path",
    "ssl.key_path",
    "ssl.p12_path",
    "ssl.pem_path",
    "prisma_url",
    "endpoint",
    "bucket",
    "region",
    "prefix",
    "access_key_id",
    "secret_access_key",
    "public_base_url",
    "domain",
]


class APIStackBlob(TypedDict):
    prefix: str
    visibility: TemplateBlobVisibility
    used_bytes: int | None
    api_key_id: str | None


class APIStackMember(TypedDict):
    resource_type: StackMemberType
    resource_id: str
    name: str
    status: ApplicationStatus | DatabaseStatus | None
    ram: int
    service_key: str | None
    database_type: int | None
    closed: bool
    blob: APIStackBlob | None


class APIStackStatus(TypedDict):
    up: int
    down: int
    building: int
    total: int


class APIStackBinding(TypedDict):
    id: str
    stack_id: str
    app_id: str
    database_id: str | None
    blob_id: str | None
    target_app_id: str | None
    env_map: dict[str, StackBindingValue]
    certs_path: str | None
    created_at: str


class APIStack(TypedDict):
    id: str
    name: str
    description: str | None
    network_mode: StackNetworkMode
    owner_id: str
    workspace_id: str | None
    members: list[APIStackMember]
    status: APIStackStatus
    ram_total: int
    bindings: list[APIStackBinding]
    template: APITemplateOrigin | None
    update_available: bool
    created_at: str
    updated_at: str


class APIStackChange(APIStack, APIRestartRequired):
    """An `APIStack` plus the apps that must restart to read the new variables or certificates."""


class APIStackBindingChange(APIStackBinding, APIRestartRequired):
    """An `APIStackBinding` plus the apps that must restart."""


class APIStackConnectionSnippet(TypedDict):
    language: ApplicationLanguage
    driver: str
    database_type: int | None
    blob: bool
    title: str
    code: str
    env_vars: list[str]


class APIStackConnectionInfo(TypedDict):
    app_id: str
    language: ApplicationLanguage
    snippets: list[APIStackConnectionSnippet]


StackSnapshotStatus = Literal["pending", "ready"]


class _APIStackSnapshotMemberRequired(TypedDict):
    resource_type: Literal["application", "database"]
    resource_id: str
    # `None` while the stack snapshot is `pending`.
    snapshot_id: str | None


class APIStackSnapshotMember(_APIStackSnapshotMemberRequired, total=False):
    # Only while the stack snapshot is `pending`: the job to follow with `snapshot_jobs`.
    job_id: str


class APIStackSnapshot(TypedDict):
    id: str
    stack_id: str
    reason: StackSnapshotReason
    # `pending` while the snapshots of the members are being taken; `ready` once every member has its snapshot
    # (a stack snapshot that failed is not listed).
    status: StackSnapshotStatus
    date: str
    size: str
    members: list[APIStackSnapshotMember]
    closed: bool


class APIStackDatabaseAdded(APIRestartRequired):
    stack: APIStack
    database_id: str
    password: str
    """The password of the new database. It comes only in this response."""


class APIStackBlobAdded(APIRestartRequired):
    stack: APIStack
    blob: APIStackMember


class APIStackDeleteResult(TypedDict):
    """What `stacks.delete` returns (HTTP 200): the resources deleted together with the stack. Both lists are empty
    and `deleted_blob` is `False` with `mode` `dissolve`."""

    deleted_apps: list[str]
    deleted_databases: list[str]
    deleted_blob: bool


class _StackBindingInputRequired(TypedDict):
    app_id: str


class StackBindingInput(_StackBindingInputRequired, total=False):
    env_map: dict[str, StackBindingValue]


class StackConnectionInput(StackBindingInput, total=False):
    """A connection sent with a create or an add: `database_id` or `target_app_id` says what it connects to."""

    database_id: str
    target_app_id: str


class StackMemberRef(TypedDict):
    resource_type: Literal["application", "database"]
    resource_id: str


class _StackCreateBodyRequired(TypedDict):
    name: str


class StackCreateBody(_StackCreateBodyRequired, total=False):
    description: str | None
    network_mode: StackNetworkMode
    members: list[StackMemberRef]
    bindings: list[StackConnectionInput]
    workspace_id: str


class _StackTransformBodyRequired(TypedDict):
    folder_id: str
    inject_variables: bool


class StackTransformBody(_StackTransformBodyRequired, total=False):
    workspace_id: str
    name: str
    bindings: list[StackConnectionInput]


class StackUpdateBody(TypedDict, total=False):
    name: str
    description: str | None


class _StackDeleteBodyRequired(TypedDict):
    mode: StackDeleteMode
    confirm_name: str


class StackDeleteBody(_StackDeleteBodyRequired, total=False):
    # What to do with the files of the stack's Blob folder.
    blob: StackBlobDisposition


class _StackMemberAddBodyRequired(TypedDict):
    resource_type: Literal["application", "database"]
    resource_id: str


class StackMemberAddBody(_StackMemberAddBodyRequired, total=False):
    bindings: list[StackConnectionInput]


class StackBindingCreateBody(StackBindingInput, total=False):
    database_id: str
    blob_id: str
    target_app_id: str


class _StackDatabaseBodyRequired(TypedDict):
    type: int
    name: str
    ram: int


class StackDatabaseBody(_StackDatabaseBodyRequired, total=False):
    version: str
    description: str | None
    bindings: list[StackBindingInput]
    # Name of the stack created when the app that receives the database is not in one yet.
    stack_name: str


class StackBlobBody(TypedDict, total=False):
    prefix: str
    visibility: TemplateBlobVisibility
    bindings: list[StackBindingInput]


class StackSnapshotRestoreBody(TypedDict, total=False):
    restore_image_version: bool


class APIStackSnapshotJob(TypedDict):
    """Job of one member of a stack snapshot (taking it or restoring it). Follow it with `snapshot_jobs` using
    `resource_id` and the scope that matches `resource_type` (`"application"` -> `"applications"`,
    `"database"` -> `"databases"`)."""

    resource_id: str
    resource_type: Literal["application", "database"]
    job_id: str


class APIStackSnapshotAccepted(TypedDict):
    """What `stacks.snapshots.create` returns (HTTP 202): the stack snapshot `id` and one snapshot job per member
    (databases first); nothing is taken yet. Each member is a regular manual snapshot. The stack snapshot is listed
    as `pending` and becomes `ready` when the last job ends; a failed one is not listed."""

    id: str
    jobs: list[APIStackSnapshotJob]


class _APIStackSnapshotRestoreMemberJobRequired(TypedDict):
    resource_id: str
    resource_type: Literal["application", "database"]
    job_id: str


class APIStackSnapshotRestoreMemberJob(_APIStackSnapshotRestoreMemberJobRequired, total=False):
    """Restore job of one member of a stack snapshot (see `APIStackSnapshotJob`)."""

    # Set when `restore_image_version` was asked but the image version recorded for this application is gone: only its
    # data is restored.
    warning: SnapshotImageWarning


class APIStackSnapshotRestoreAccepted(TypedDict):
    """What `stacks.snapshots.restore` returns (HTTP 202): one job per member, databases first, and nothing is
    restored yet. The stack is restored when every job is `ready`; after a failed
    member the jobs behind it end `failed` with `STACK_RESTORE_MEMBER_FAILED`."""

    jobs: list[APIStackSnapshotRestoreMemberJob]


class APIStackSnapshotCreateAndWaitResult(APIStackSnapshotAccepted):
    """What `stacks.snapshots.create_and_wait` returns: the accepted answer and the final job of each member."""

    finished: list[APISnapshotJob]


class APIStackSnapshotRestoreAndWaitResult(APIStackSnapshotRestoreAccepted):
    """What `stacks.snapshots.restore_and_wait` returns: the accepted answer and the final job of each member."""

    finished: list[APISnapshotJob]


# -- API keys (listed by the dashboard; the SDK has no route for them, the types serve code that decodes them)


class APIApiKeyManager(TypedDict):
    """The stack the platform created an API key for. Such a key is revoked when the stack is dissolved or deleted."""

    type: Literal["stack"]
    id: str


class _APIApiKeyRequired(TypedDict):
    id: str
    name: str
    prefix: str
    last4: str | None
    scopes: list[str]
    allowed_ips: list[str]
    created_at: str
    last_used_at: str | None


class APIApiKey(_APIApiKeyRequired, total=False):
    # Blob folder the key is restricted to (ends in `/`); `None` = the whole Blob. A restricted key only works with
    # the `blob:*` scopes and is refused account-level Blob operations with `BLOB_PREFIX_DENIED`.
    blob_prefix: str | None
    # Set when the platform created the key for a stack (`API_KEY_MANAGED` on manual changes); `None` otherwise.
    managed_by: APIApiKeyManager | None


# -- Web Analytics (`GET /v1/apps/:id/analytics*`) ---------------------------------------------

# What the traffic can be broken down and filtered by: each value is a key of
# `APIApplicationAnalyticsTraffic["breakdowns"]` and the name of a filter of the analytics routes.
ApplicationAnalyticsDimension = Literal[
    "country",
    "edge_location",
    "host",
    "path",
    "method",
    "status",
    "protocol",
    "device",
    "os",
    "browser",
    "referer",
    "asn",
    "ip",
    "content_type",
    "cache_status",
    "bot",
]

# Value of a dimension for a request that has nothing for it; accepted as a filter value.
ANALYTICS_NO_VALUE = "(none)"

# Size of each point of a time series, chosen by the API from the length of the window.
ApplicationAnalyticsInterval = Literal["1m", "5m", "15m", "1h"]

# Class of HTTP status accepted by the `status` filter.
ApplicationAnalyticsStatusClass = Literal["2xx", "3xx", "4xx", "5xx"]

# Order of the request log by time.
ApplicationAnalyticsOrder = Literal["asc", "desc"]


class AnalyticsFilters(TypedDict, total=False):
    """Filters of the analytics routes, one per dimension; all of them together narrow every part of the answer.
    Each takes one value, as found in a breakdown entry or a request of the log (`ANALYTICS_NO_VALUE` for requests
    with no value). `path` is a prefix and `status` also takes a class (`5xx`)."""

    country: str
    edge_location: str
    host: str
    path: str
    method: str
    status: str
    protocol: str
    device: str
    os: str
    browser: str
    referer: str
    asn: str
    ip: str
    content_type: str
    cache_status: str
    bot: str


class APIApplicationAnalyticsMeta(TypedDict):
    """Fields every analytics answer carries. An app with no site published answers `web_published: False`."""

    start: str  # start of the window actually read (ISO 8601); may be rounded
    end: str
    hosts: list[str]  # hostnames of the app that were read
    web_published: bool
    sampled: bool  # numbers estimated from a sample (and the request log is a sample)
    stale: bool  # `True` when the latest data could not be read and this is an earlier answer; see `generated_at`
    generated_at: str
    history_days: int  # how many days back the plan of the app's owner can read


class APIApplicationAnalyticsSeriesMeta(APIApplicationAnalyticsMeta):
    interval: ApplicationAnalyticsInterval


class APIApplicationAnalyticsBreakdownEntry(TypedDict):
    """One entry of a breakdown, ordered by `requests` (highest first)."""

    value: str  # send it as the filter of the same name; `(none)` = the request had no value
    label: str | None  # readable name when `value` is a code (an `asn` network name)
    requests: int
    visits: int
    bytes: int


class APIApplicationAnalyticsTrafficSummary(TypedDict):
    requests: int
    visits: int
    bytes: int
    errors_4xx: int
    errors_5xx: int
    error_rate_4xx: float  # 0 to 1
    error_rate_5xx: float
    edge_time_p95_ms: float


class APIApplicationAnalyticsTrafficPoint(TypedDict):
    time: str  # start of the point
    requests: int
    visits: int
    bytes: int
    errors_4xx: int
    errors_5xx: int


class APIApplicationAnalyticsTrafficPeriod(TypedDict):
    """The previous period (same length, right before the window), sent when `compare=True`."""

    start: str
    end: str
    summary: APIApplicationAnalyticsTrafficSummary | None
    series: list[APIApplicationAnalyticsTrafficPoint]


class APIApplicationAnalyticsTraffic(APIApplicationAnalyticsSeriesMeta):
    """`GET /v1/apps/:id/analytics`."""

    summary: APIApplicationAnalyticsTrafficSummary | None  # `None` when there was no request
    series: list[APIApplicationAnalyticsTrafficPoint]
    previous: APIApplicationAnalyticsTrafficPeriod | None  # `None` unless `compare=True`
    # Top entries per dimension: only the dimensions asked for in `breakdowns`, or all when omitted.
    breakdowns: dict[ApplicationAnalyticsDimension, list[APIApplicationAnalyticsBreakdownEntry]]


class APIApplicationAnalyticsErrorsSummary(TypedDict):
    requests: int
    errors: int  # `errors_5xx`, plus `errors_4xx` with `include_4xx=True`
    error_rate: float  # 0 to 1
    errors_4xx: int
    errors_5xx: int


class APIApplicationAnalyticsErrorsPoint(TypedDict):
    time: str
    requests: int
    errors_4xx: int
    errors_5xx: int


class APIApplicationAnalyticsErrorsPeriod(TypedDict):
    start: str
    end: str
    summary: APIApplicationAnalyticsErrorsSummary | None
    series: list[APIApplicationAnalyticsErrorsPoint]


class APIApplicationAnalyticsErrorEntry(TypedDict):
    value: str
    requests: int
    errors: int
    error_rate: float


class APIApplicationAnalyticsErrors(APIApplicationAnalyticsSeriesMeta):
    """`GET /v1/apps/:id/analytics/errors`."""

    include_4xx: bool
    summary: APIApplicationAnalyticsErrorsSummary | None
    series: list[APIApplicationAnalyticsErrorsPoint]
    previous: APIApplicationAnalyticsErrorsPeriod | None
    paths: list[APIApplicationAnalyticsErrorEntry]  # highest `errors` first; `value` is the path
    statuses: list[APIApplicationAnalyticsBreakdownEntry]  # `value` is the status, such as `502`


class APIApplicationAnalyticsLatency(TypedDict):
    avg_ms: float
    p50_ms: float
    p75_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    p999_ms: float  # 99.9th percentile


class APIApplicationAnalyticsLatencyBrief(TypedDict):
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


class APIApplicationAnalyticsPerformanceSummary(TypedDict):
    requests: int
    edge: APIApplicationAnalyticsLatency  # the whole time the visitor waited for the first byte
    # The part your app took; `None` when the request did not reach the app.
    container: APIApplicationAnalyticsLatency | None


class APIApplicationAnalyticsPerformancePoint(TypedDict):
    time: str
    requests: int
    edge: APIApplicationAnalyticsLatencyBrief
    container: APIApplicationAnalyticsLatencyBrief | None


class APIApplicationAnalyticsPerformancePeriod(TypedDict):
    start: str
    end: str
    summary: APIApplicationAnalyticsPerformanceSummary | None
    series: list[APIApplicationAnalyticsPerformancePoint]


class APIApplicationAnalyticsLatencyEntry(TypedDict):
    value: str
    label: str | None
    requests: int
    edge: APIApplicationAnalyticsLatencyBrief
    container: APIApplicationAnalyticsLatencyBrief | None


class APIApplicationAnalyticsPathIssue(TypedDict):
    path: str
    requests: int
    errors: int  # 5xx
    error_rate: float
    avg_ms: float  # average edge time
    p99_ms: float


class APIApplicationAnalyticsPerformance(APIApplicationAnalyticsSeriesMeta):
    """`GET /v1/apps/:id/analytics/performance`. Needs a plan with `features.web_analytics_performance`."""

    summary: APIApplicationAnalyticsPerformanceSummary | None
    series: list[APIApplicationAnalyticsPerformancePoint]
    previous: APIApplicationAnalyticsPerformancePeriod | None
    countries: list[APIApplicationAnalyticsLatencyEntry]
    edge_locations: list[APIApplicationAnalyticsLatencyEntry]
    slow_paths: list[APIApplicationAnalyticsLatencyEntry]  # slowest first, by the edge p95
    path_issues: list[APIApplicationAnalyticsPathIssue]  # most requested first


class APIApplicationAnalyticsRequest(TypedDict):
    """One request of the log. Fields named after a dimension hold the same value as that dimension."""

    time: str
    request_id: str  # request identifier
    host: str
    path: str
    query: str  # without the leading `?`; empty when none
    method: str
    protocol: str
    status: int
    container_status: int | None  # `None` when the request did not reach the app
    edge_time_ms: float
    container_time_ms: float | None
    ip: str
    asn: int
    asn_name: str
    country: str
    edge_location: str
    referer: str  # `(none)` = direct visit
    referer_url: str | None
    device: str
    os: str
    browser: str
    bot: str
    content_type: str
    cache_status: str


class APIApplicationAnalyticsRequestList(APIApplicationAnalyticsMeta):
    """`GET /v1/apps/:id/analytics/requests`. Needs a plan with `features.web_analytics_requests`."""

    order: ApplicationAnalyticsOrder
    requests: list[APIApplicationAnalyticsRequest]
    cursor: str | None  # pass back as `cursor` for the next page; `None` = last page


class APIApplicationAnalyticsRangeExceedsPlanDetails(TypedDict):
    """`details` of `ANALYTICS_RANGE_EXCEEDS_PLAN`."""

    history_days: int
    earliest: str  # earliest `start` accepted right now (ISO 8601)
