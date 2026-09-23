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
print(f"Hi {me['name']}! Plan: {me['plan']['name']}")

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
    # base_url, user_agent and a custom transport are also accepted
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

Nested resources are attributes: `client.apps.deploys`, `client.apps.envs`, `client.workspaces.members`, `client.billing.orders`, …

### Apps

```python
app = client.apps.get(app_id)

client.apps.restart(app_id)  # normal restart
client.apps.restart(app_id, {"reinstall_dependencies": True})

metrics = client.apps.metrics(app_id, range="24h")
logs = client.apps.logs(app_id)
```

### Uploading and downloading

Uploads take `bytes`; downloads return `bytes`.

```python
with open("app.zip", "rb") as f:
    app = client.apps.create({"name": "my-app", "memory": 512}, file=f.read())

with open("backup.zip", "wb") as f:
    f.write(client.apps.download(app_id))
```

`client.snapshots.download` works the same way.

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
| Apps | `client.apps` (+ `.deploys`, `.network`, `.envs`, `.files`) | 36 |
| Databases | `client.databases` (+ `.credentials`) | 13 |
| Snapshots | `client.snapshots` | 5 |
| Account | `client.account` (+ `.sessions`, `.folders`, `.favorites`) | 10 |
| Workspaces | `client.workspaces` (+ `.members`, `.roles`, `.invites`, `.action_requests`, `.apps`, `.databases`, `.folders`, `.favorites`) | 30 |
| Billing | `client.billing` (+ `.orders`) | 5 |

Dashboard-only features (activity log, notifications, API key management, the database **Data** tab, plan downgrade, creating workspace invites, transferring workspace ownership and approving action requests) are not part of the public API. See [what an API key cannot do](https://docs.vertracloud.app/sdks).

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
