# Vertra Cloud Python SDK

[![PyPI](https://img.shields.io/pypi/v/vertracloud-api.svg)](https://pypi.org/project/vertracloud-api/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Official Python SDK for the [Vertra Cloud](https://vertracloud.app) public API: apps, databases, snapshots, account, workspaces and billing — one typed method per route.

- Python 3.10+, fully typed (`py.typed`), with `TypedDict` payloads.
- Zero dependencies outside the standard library.
- No hidden retries, caching or state: errors come back as they happened.

## Installation

```bash
pip install vertracloud-api
```

## Getting an API key

Sign in to the [dashboard](https://vertracloud.app), open **Settings → API keys** and create a key with only the scopes your code needs (e.g. `apps:read`, `apps:write`). Keep it out of your source code — the examples read it from `VERTRA_API_KEY`.

## Quick start

```python
import os

from vertracloud import VertraClient

client = VertraClient(api_key=os.environ["VERTRA_API_KEY"])

me = client.account.get()
plan = me["plan"]
print(f"Hi {me['name']}! Plan: {plan['name'] if plan else 'none'}")

for app in me["applications"]:
    print(app["id"], app["name"], app["status"])
```

## Documentation

- Guide: [docs.vertracloud.app/sdks](https://docs.vertracloud.app/sdks)
- API reference and scopes: [docs.vertracloud.app/api-reference](https://docs.vertracloud.app/api-reference/introduction)

Every method has a docstring with its HTTP route and the API key scope it needs.

## Usage

### Client options

```python
client = VertraClient(
    api_key=os.environ["VERTRA_API_KEY"],
    timeout=10,  # seconds, default 30 per call
    # base_url, blob_base_url, user_agent and a custom transport are also accepted
)
```

### Per-call options

Methods on apps and databases take a keyword-only `workspace_id`; downloads, uploads and streams also take `timeout`:

```python
# Act on a resource that belongs to a workspace
app = client.apps.get(app_id, workspace_id=workspace_id)

# Give one slow call more time
zip_bytes = client.apps.download(app_id, timeout=300)
```

Nested resources are attributes: `client.apps.deploys`, `client.apps.releases`, `client.apps.envs`, `client.workspaces.members`, `client.billing.orders`, …

### Apps

```python
app = client.apps.get(app_id)

client.apps.restart(app_id)  # normal restart
client.apps.restart(app_id, {"reinstall_dependencies": True})

metrics = client.apps.metrics(app_id, range="24h")
logs = client.apps.logs(app_id)
```

### Custom domains

An app can have several domains, each with its own port, path prefix or redirect. `add` returns the created
domain and its automatic `www` (or root) companion; the limit depends on your plan.

```python
domains = client.apps.domains.add(app_id, {"hostname": "example.com", "port": 8080})
main = domains[0]

for record in client.apps.domains.dns(app_id, main["id"]):
    print(record["type"], record["name"], record["value"], record["status"])

client.apps.domains.update(app_id, domains[1]["id"], {"redirect_to": main["id"], "redirect_status": 301})
client.apps.domains.remove(app_id, main["id"])
```

`client.apps.domains.connect(app_id, domain_id)` returns a link that configures the DNS records at providers that
support it, or raises a 404 `DOMAIN_CONNECT_UNAVAILABLE`.

### Releases and rollback

```python
page = client.apps.releases.list(app_id, limit=20)  # newest first, max 50 per page
release_id = page["data"][1]["id"]

log = client.apps.releases.log(app_id, release_id)  # log["content"] is None when absent or expired

# Preview what restoring the saved environment variables would change.
# The preview returns variable names only, never values.
preview = client.apps.releases.preview_rollback(app_id, release_id)
for change in preview["environment_changes"]:
    print(change["key"], change["change"])  # added | modified | removed

# Restores the release's code and restarts the app. Variables are kept unless you ask for them.
new_release = client.apps.releases.rollback(app_id, release_id, {"restore_environment": True})
```

`rollback` needs `apps:write`; with `restore_environment` the key also needs `apps:envs`, as does the preview. Deploy behavior is set through `update_config`:

```python
client.apps.update_config(
    app_id, {"deploy": {"zero_downtime": "auto", "auto_rollback": True, "health_check_path": "/health"}}
)
client.apps.update_config(app_id, {"deploy": {"health_check_path": None}})  # clears the path
```

`client.apps.files.upload(..., message="...")` sets the message shown in the release history.

### Uploading and downloading

Uploads take `bytes`; downloads return `bytes`.

```python
with open("app.zip", "rb") as f:
    app = client.apps.create({"name": "my-app", "memory": 512}, file=f.read())

with open("backup.zip", "wb") as f:
    f.write(client.apps.download(app_id))
```

`client.snapshots.download` works the same way.

### Waiting for the first build

`apps.create` replies right away with `status: "building"`. Wait for the build to end:

```python
app = client.apps.create({"name": "my-app", "memory": 512}, file=data)
try:
    app = client.apps.wait_until_ready(app["id"], timeout=600, interval=2)  # status is "up"
# ended "down": e.code is app["last_build_error"] (e.g. "INSTALL_OUT_OF_MEMORY"), "APP_DOWN" if none
except vertracloud.AppBuildFailedError as e:
    print(client.apps.logs(app["id"]))
except vertracloud.WaitTimeoutError:  # still building after `timeout` seconds
    ...
```

While the build runs, calls that need a stopped or running app can fail with `APP_BUILDING` (409).

### Realtime logs (SSE)

```python
stream = client.apps.realtime(app_id)
try:
    for event in stream:
        print(event.event, event.data)
finally:
    stream.close()
```

Stop the stream with `break` or `stream.close()`. Pass `since=` to resume. There is no automatic reconnection.

### Blob Storage

`client.blob` talks to the Blob Storage API (`blob_base_url`, default `https://blob.vertracloud.app/v1`) with the same API key (`blob:read` / `blob:write`). Every method accepts `workspace_id`.

```python
obj = client.blob.put(
    "images/logo.png",
    "./logo.png",
    visibility="public",
    on_progress=lambda loaded, total: print(loaded, total),
)
print(obj["url"])

for o in client.blob.list(prefix="images/"):  # follows the cursor for you
    print(o["path"], o["size"])

link = client.blob.download_url(obj["id"], expires_in=600)  # {"url", "expires_at"}
client.blob.delete_many(prefix="tmp/")
```

`data` can be `bytes`, a file path, or a seekable binary file. Up to 5 MB it is one request; larger files go straight to storage in parts, with a retry per part. If the process dies halfway, `client.blob.resume(upload_id, data)` sends only the missing parts.

### Errors

Every non-2xx response raises a `VertraAPIError` carrying the HTTP `status`, the API `code` (e.g. `APP_NOT_FOUND`) and `details`; `str(err)` includes the message. The API key is never part of the error, even when it is printed:

```python
from vertracloud import NotFoundError, RateLimitError, VertraAPIError

try:
    client.apps.get(app_id)
except NotFoundError:
    ...  # 404
except RateLimitError as err:
    print("retry after", err.retry_after, "s")
except VertraAPIError as err:
    print(err.status, err.code, err)
```

Other subclasses: `AuthenticationError` (401), `ScopeDeniedError` (403 — including a missing key scope) and `ValidationError` (400/422). The error codes are listed in the [API reference](https://docs.vertracloud.app/api-reference/introduction).

### Testing your code

Pass your own `vertracloud.Transport` to the client to answer requests without touching the network:

```python
client = VertraClient(api_key="test", transport=my_fake_transport)
```

## Coverage

| Domain | Resource | Routes |
|---|---|---|
| Apps | `client.apps` (+ `.deploys`, `.releases`, `.domains`, `.network`, `.envs`, `.files`) | 42 |
| Databases | `client.databases` (+ `.credentials`) | 13 |
| Snapshots | `client.snapshots` | 5 |
| Account | `client.account` (+ `.sessions`, `.folders`, `.favorites`) | 10 |
| Workspaces | `client.workspaces` (+ `.members`, `.roles`, `.invites`, `.action_requests`, `.apps`, `.databases`, `.folders`, `.favorites`) | 30 |
| Billing | `client.billing` (+ `.orders`) | 7 |
| Blob Storage | `client.blob` (+ `.shares`, `.rules`, `.domains`) | own host |

Dashboard-only features (activity log, notifications, API key management, the database **Data** tab, plan downgrade, creating workspace invites, card payments, saved cards, automatic renewal, coupon preview, receipts and approving action requests) are not part of the public API. See [what an API key cannot do](https://docs.vertracloud.app/sdks).

## Versioning

The SDK follows semantic versioning. Until `1.0.0`, minor releases may contain breaking changes; they are always called out in the [changelog](CHANGELOG.md).

## Contributing

Issues and pull requests are welcome. Before sending a change, run:

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check . && mypy src && python -m pytest -q
```

## License

[MIT](LICENSE)
