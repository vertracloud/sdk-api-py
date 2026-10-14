"""`blob` domain — Blob Storage, served by its own base URL (`blob_base_url`, default
`https://blob.vertracloud.app/v1`) with the same API key (scopes `blob:read` / `blob:write`).

Every method takes a keyword-only `workspace_id` to act on the blob of a workspace owner.
`put` picks the upload path by size: up to 5 MB it is a single multipart request; above that
the bytes go straight to storage through presigned URLs (one PUT, or several parts).
"""

from __future__ import annotations

import builtins
import contextlib
import io
import json
import os
import time
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any

from ..client import MultipartField, VertraClientError, encode_path_param
from ..errors import VertraAPIError
from ..types import (
    APIBlobBatchResult,
    APIBlobCustomDomain,
    APIBlobDeleteResult,
    APIBlobDownload,
    APIBlobObject,
    APIBlobObjectList,
    APIBlobRules,
    APIBlobS3Credentials,
    APIBlobShare,
    APIBlobStats,
    APIBlobUpload,
    APIBlobUploadPart,
    APIBlobUploadToken,
    BlobRuleInput,
    BlobVisibility,
)

if TYPE_CHECKING:
    from ..client import VertraClient

# Up to this size `put` sends one multipart request through the API; above it, a direct upload.
SIMPLE_UPLOAD_MAX_BYTES = 5 * 1024 * 1024
PART_URL_BATCH = 100
PART_ATTEMPTS = 3

BlobData = bytes | bytearray | memoryview | str | Path | IO[bytes]
ProgressCallback = Callable[[int, int], None]


def _iso(value: str | datetime | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else value


def _ws(workspace_id: str | None) -> dict[str, Any]:
    return {"workspace_id": workspace_id}


@contextlib.contextmanager
def _open_source(data: BlobData) -> Iterator[tuple[IO[bytes], int, str | None]]:
    """Yields `(seekable binary file, size, filename)` for bytes, a path, or a sized file-like."""
    if isinstance(data, (bytes, bytearray, memoryview)):
        yield io.BytesIO(bytes(data)), len(data), None
    elif isinstance(data, (str, Path)):
        with open(data, "rb") as fh:
            yield fh, os.fstat(fh.fileno()).st_size, os.path.basename(data)
    else:
        if not (hasattr(data, "read") and hasattr(data, "seek") and hasattr(data, "tell")):
            raise TypeError("data must be bytes, a file path, or a seekable binary file-like object")
        pos = data.tell()
        size = data.seek(0, os.SEEK_END) - pos
        data.seek(pos)
        yield data, size, os.path.basename(getattr(data, "name", "") or "") or None


def _read_at(fh: IO[bytes], start: int, offset: int, length: int) -> bytes:
    fh.seek(start + offset)
    chunk = fh.read(length)
    if len(chunk) != length:
        raise VertraClientError("data ended before the expected size; was the source modified during upload?")
    return chunk


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, VertraAPIError):
        return exc.status >= 500 or exc.status == 429
    return isinstance(exc, OSError)  # connection reset, timeout, DNS


class BlobSharesResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def create(
        self,
        object_id: str,
        *,
        expires_in: int | None = None,
        max_downloads: int | None = None,
        password: str | None = None,
        workspace_id: str | None = None,
    ) -> APIBlobShare:
        """POST /shares — scope `blob:write`."""
        body = {"object_id": object_id, "expires_in": expires_in, "max_downloads": max_downloads, "password": password}
        return self._c.request_json(
            "POST",
            "/shares",
            json_body={k: v for k, v in body.items() if v is not None},
            query=_ws(workspace_id),
            base_url=self._c.blob_base_url,
        )

    def list(self, object_id: str | None = None, *, workspace_id: str | None = None) -> list[APIBlobShare]:
        """GET /shares — scope `blob:read`."""
        return self._c.request_json(
            "GET", "/shares", query={"object_id": object_id, **_ws(workspace_id)}, base_url=self._c.blob_base_url
        )

    def revoke(self, share_id: str, *, workspace_id: str | None = None) -> None:
        """DELETE /shares/:id — scope `blob:write`."""
        self._c.request_json(
            "DELETE", f"/shares/{encode_path_param(share_id)}", query=_ws(workspace_id), base_url=self._c.blob_base_url
        )


class BlobRulesResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def get(self, *, workspace_id: str | None = None) -> APIBlobRules:
        """GET /rules — scope `blob:read`. Keep the returned `etag` for `set`."""
        return self._c.request_json("GET", "/rules", query=_ws(workspace_id), base_url=self._c.blob_base_url)

    def set(self, rules: list[BlobRuleInput], etag: str, *, workspace_id: str | None = None) -> APIBlobRules:
        """PUT /rules — replaces the whole list; `etag` goes in `If-Match` (409 `BLOB_RULES_CONFLICT` if stale)."""
        return self._c.request_json(
            "PUT",
            "/rules",
            json_body={"rules": rules},
            query=_ws(workspace_id),
            base_url=self._c.blob_base_url,
            extra_headers={"If-Match": etag},
        )

    def put(self, prefix: str, *, workspace_id: str | None = None, **rule: Any) -> APIBlobRules:
        """PUT /rules/:prefix — creates or changes one rule (`visibility`, `max_size`, `delete_after_days`, ...)."""
        return self._c.request_json(
            "PUT",
            f"/rules/{encode_path_param(prefix)}",
            json_body=rule,
            query=_ws(workspace_id),
            base_url=self._c.blob_base_url,
        )

    def delete(self, prefix: str, *, workspace_id: str | None = None) -> APIBlobRules:
        """DELETE /rules/:prefix — returns the remaining rules."""
        return self._c.request_json(
            "DELETE", f"/rules/{encode_path_param(prefix)}", query=_ws(workspace_id), base_url=self._c.blob_base_url
        )


class BlobDomainsResource:
    def __init__(self, client: VertraClient) -> None:
        self._c = client

    def list(self, *, workspace_id: str | None = None) -> list[APIBlobCustomDomain]:
        """GET /domains — scope `blob:read`."""
        return self._c.request_json("GET", "/domains", query=_ws(workspace_id), base_url=self._c.blob_base_url)

    def add(
        self,
        hostname: str,
        prefix: str | None = None,
        *,
        web_content: bool | None = None,
        workspace_id: str | None = None,
    ) -> APIBlobCustomDomain:
        """POST /domains — scope `blob:write`. `web_content=True` serves HTML/SVG/XML in the browser (sandboxed)."""
        body = {
            "hostname": hostname,
            **({"prefix": prefix} if prefix is not None else {}),
            **({"web_content": web_content} if web_content is not None else {}),
        }
        return self._c.request_json(
            "POST", "/domains", json_body=body, query=_ws(workspace_id), base_url=self._c.blob_base_url
        )

    def update(self, domain_id: str, *, web_content: bool, workspace_id: str | None = None) -> APIBlobCustomDomain:
        """PATCH /domains/:id — scope `blob:write`."""
        return self._c.request_json(
            "PATCH",
            f"/domains/{encode_path_param(domain_id)}",
            json_body={"web_content": web_content},
            query=_ws(workspace_id),
            base_url=self._c.blob_base_url,
        )

    def verify(self, domain_id: str, *, workspace_id: str | None = None) -> APIBlobCustomDomain:
        """POST /domains/:id/verify — asks for a new CNAME/SSL check."""
        return self._c.request_json(
            "POST",
            f"/domains/{encode_path_param(domain_id)}/verify",
            json_body={},
            query=_ws(workspace_id),
            base_url=self._c.blob_base_url,
        )

    def delete(self, domain_id: str, *, workspace_id: str | None = None) -> None:
        """DELETE /domains/:id."""
        self._c.request_json(
            "DELETE",
            f"/domains/{encode_path_param(domain_id)}",
            query=_ws(workspace_id),
            base_url=self._c.blob_base_url,
        )


class BlobResource:
    """`client.blob.*` — objects, uploads, shares, folder rules, domains, stats."""

    def __init__(self, client: VertraClient) -> None:
        self._c = client
        self.shares = BlobSharesResource(client)
        self.rules = BlobRulesResource(client)
        self.domains = BlobDomainsResource(client)

    def _json(self, method: str, path: str, **kw: Any) -> Any:
        return self._c.request_json(method, path, base_url=self._c.blob_base_url, **kw)

    # -- upload ----------------------------------------------------------

    def put(
        self,
        path: str,
        data: BlobData,
        *,
        visibility: BlobVisibility | None = None,
        overwrite: bool | None = None,
        random_suffix: bool | None = None,
        cache_control: str | None = None,
        content_disposition: str | None = None,
        filename: str | None = None,
        expires_at: str | datetime | None = None,
        metadata: dict[str, str] | None = None,
        on_progress: ProgressCallback | None = None,
        workspace_id: str | None = None,
    ) -> APIBlobObject:
        """Uploads `data` (bytes, file path, or seekable binary file) to `path`; returns the object.

        Up to 5 MB: `POST /objects` (multipart). Larger: `POST /uploads`, then a presigned
        PUT (single) or parts (multipart) and `/complete`. `on_progress(loaded, total)` is
        called as bytes are sent. If a large upload is interrupted, call `resume`.
        """
        opts: dict[str, Any] = {
            "visibility": visibility,
            "overwrite": overwrite,
            "random_suffix": random_suffix,
            "cache_control": cache_control,
            "content_disposition": content_disposition,
            "filename": filename,
            "expires_at": _iso(expires_at),
        }
        with _open_source(data) as (fh, size, name):
            start = fh.tell()
            if size <= SIMPLE_UPLOAD_MAX_BYTES:
                query = {**opts, "path": path, "metadata": json.dumps(metadata) if metadata else None}
                query.update(_ws(workspace_id))
                payload = _read_at(fh, start, 0, size)
                obj = self._c.request_multipart(
                    "POST",
                    "/objects",
                    fields=[MultipartField("file", payload, filename=name or os.path.basename(path))],
                    query=query,
                    base_url=self._c.blob_base_url,
                )
                if on_progress:
                    on_progress(size, size)
                return obj
            body = {
                k: v for k, v in {**opts, "path": path, "size": size, "metadata": metadata}.items() if v is not None
            }
            upload = self._json("POST", "/uploads", json_body=body, query=_ws(workspace_id))
            return self._send(upload, fh, start, size, on_progress, workspace_id)

    def resume(
        self,
        upload_id: str,
        data: BlobData,
        *,
        on_progress: ProgressCallback | None = None,
        workspace_id: str | None = None,
    ) -> APIBlobObject:
        """Continues an interrupted direct upload with the same data: sends only the missing parts."""
        upload = self._json("GET", f"/uploads/{encode_path_param(upload_id)}", query=_ws(workspace_id))
        with _open_source(data) as (fh, size, _name):
            if size != upload["size"]:
                raise ValueError("data size does not match the upload being resumed")
            return self._send(upload, fh, fh.tell(), size, on_progress, workspace_id)

    def _send(
        self,
        upload: APIBlobUpload,
        fh: IO[bytes],
        start: int,
        size: int,
        on_progress: ProgressCallback | None,
        workspace_id: str | None,
    ) -> APIBlobObject:
        base = f"/uploads/{encode_path_param(upload['id'])}"
        loaded = 0
        if upload["mode"] == "single":
            self._c.request_presigned("PUT", upload["url"], upload["headers"], _read_at(fh, start, 0, size))
            if on_progress:
                on_progress(size, size)
        else:
            part_size = upload["part_size"]
            done = set(upload.get("uploaded_parts") or [])
            numbers = range(1, upload["part_count"] + 1)
            loaded = sum(min(part_size, size - (n - 1) * part_size) for n in done)
            if on_progress and loaded:
                on_progress(loaded, size)
            missing = [n for n in numbers if n not in done]
            for i in range(0, len(missing), PART_URL_BATCH):
                batch: list[APIBlobUploadPart] = self._json(
                    "POST",
                    f"{base}/parts",
                    json_body={"part_numbers": missing[i : i + PART_URL_BATCH]},
                    query=_ws(workspace_id),
                )
                for part in batch:
                    chunk = _read_at(fh, start, (part["part_number"] - 1) * part_size, part["size"])
                    self._put_part(part, chunk)
                    loaded += part["size"]
                    if on_progress:
                        on_progress(loaded, size)
        return self._json("POST", f"{base}/complete", json_body={}, query=_ws(workspace_id))

    def _put_part(self, part: APIBlobUploadPart, chunk: bytes) -> None:
        for attempt in range(PART_ATTEMPTS):
            try:
                self._c.request_presigned("PUT", part["url"], part["headers"], chunk)
                return
            except Exception as exc:
                if attempt == PART_ATTEMPTS - 1 or not _retryable(exc):
                    raise
                time.sleep(0.25 * 2**attempt)

    def abort_upload(self, upload_id: str, *, workspace_id: str | None = None) -> None:
        """DELETE /uploads/:id — idempotent."""
        self._json("DELETE", f"/uploads/{encode_path_param(upload_id)}", query=_ws(workspace_id))

    def uploads(self, *, workspace_id: str | None = None) -> list[APIBlobUpload]:
        """GET /uploads — direct uploads still in progress."""
        return self._json("GET", "/uploads", query=_ws(workspace_id))

    # -- objects ---------------------------------------------------------

    def list(
        self,
        prefix: str | None = None,
        delimiter: str | None = None,
        visibility: BlobVisibility | None = None,
        *,
        limit: int | None = None,
        workspace_id: str | None = None,
    ) -> Iterator[APIBlobObject]:
        """GET /objects — iterator over every object, following the cursor page by page.

        Use `list_page` to also get the `folders` that `delimiter` produces.
        """
        cursor: str | None = None
        while True:
            page = self.list_page(prefix, delimiter, visibility, cursor=cursor, limit=limit, workspace_id=workspace_id)
            yield from page["objects"]
            cursor = page["cursor"]
            if not cursor:
                return

    def list_page(
        self,
        prefix: str | None = None,
        delimiter: str | None = None,
        visibility: BlobVisibility | None = None,
        *,
        cursor: str | None = None,
        limit: int | None = None,
        workspace_id: str | None = None,
    ) -> APIBlobObjectList:
        """GET /objects — one page: `{objects, folders, cursor}`."""
        query = {
            "prefix": prefix,
            "delimiter": delimiter,
            "visibility": visibility,
            "cursor": cursor,
            "limit": limit,
            **_ws(workspace_id),
        }
        return self._json("GET", "/objects", query=query)

    def get(self, id: str, *, workspace_id: str | None = None) -> APIBlobObject:
        """GET /objects/:id."""
        return self._json("GET", f"/objects/{encode_path_param(id)}", query=_ws(workspace_id))

    def update(self, id: str, *, workspace_id: str | None = None, **changes: Any) -> APIBlobObject:
        """PATCH /objects/:id — `visibility`, `cache_control`, `content_disposition`, `filename`,
        `expires_at`, `metadata`. `None` resets a field; a `None` metadata value removes that key."""
        if "expires_at" in changes:
            changes["expires_at"] = _iso(changes["expires_at"])
        return self._json("PATCH", f"/objects/{encode_path_param(id)}", json_body=changes, query=_ws(workspace_id))

    def update_many(
        self, ids: builtins.list[str], *, workspace_id: str | None = None, **changes: Any
    ) -> builtins.list[APIBlobBatchResult]:
        """PATCH /objects — applies `changes` to many ids (sent in batches of 100)."""
        if "expires_at" in changes:
            changes["expires_at"] = _iso(changes["expires_at"])
        results: builtins.list[APIBlobBatchResult] = []
        for i in range(0, len(ids), 100):
            results += self._json(
                "PATCH",
                "/objects",
                json_body={"ids": ids[i : i + 100], "changes": changes},
                query=_ws(workspace_id),
            )
        return results

    def copy(self, id: str, path: str, *, workspace_id: str | None = None, **opts: Any) -> APIBlobObject:
        """POST /objects/copy — `overwrite`, `random_suffix`, `visibility`, `move` as options."""
        return self._json(
            "POST", "/objects/copy", json_body={"source": id, "path": path, **opts}, query=_ws(workspace_id)
        )

    def move(self, id: str, path: str, *, workspace_id: str | None = None, **opts: Any) -> APIBlobObject:
        """Same as `copy` with `move=True`: the object keeps its id and gets the new path."""
        return self.copy(id, path, workspace_id=workspace_id, **{**opts, "move": True})

    def delete(self, id: str, *, workspace_id: str | None = None) -> None:
        """DELETE /objects/:id."""
        self._json("DELETE", f"/objects/{encode_path_param(id)}", query=_ws(workspace_id))

    def delete_many(
        self, ids: builtins.list[str] | None = None, prefix: str | None = None, *, workspace_id: str | None = None
    ) -> APIBlobDeleteResult:
        """DELETE /objects — by `ids` or by `prefix`; repeats while the server reports `remaining`."""
        if (ids is None) == (prefix is None):
            raise ValueError("pass exactly one of ids or prefix")
        bodies = (
            [{"prefix": prefix}]
            if prefix is not None
            else [{"ids": (ids or [])[i : i + 1000]} for i in range(0, len(ids or []), 1000)]
        )
        total: APIBlobDeleteResult = {"deleted": [], "not_found": [], "remaining": False}
        for body in bodies:
            while True:
                res: APIBlobDeleteResult = self._json("DELETE", "/objects", json_body=body, query=_ws(workspace_id))
                total["deleted"] += res["deleted"]
                total["not_found"] += res["not_found"]
                if not res["remaining"] or not (res["deleted"] or res["not_found"]):
                    break
        return total

    def download_url(
        self,
        id: str,
        expires_in: int | None = None,
        disposition: str | None = None,
        filename: str | None = None,
        *,
        workspace_id: str | None = None,
    ) -> APIBlobDownload:
        """GET /objects/:id/download with `redirect=false` — returns `{url, expires_at}`."""
        query = {
            "expires_in": expires_in,
            "disposition": disposition,
            "filename": filename,
            "redirect": False,
            **_ws(workspace_id),
        }
        return self._json("GET", f"/objects/{encode_path_param(id)}/download", query=query)

    # -- account ---------------------------------------------------------

    def stats(self, *, workspace_id: str | None = None) -> APIBlobStats:
        """GET /stats — usage, quota and plan limits."""
        return self._json("GET", "/stats", query=_ws(workspace_id))

    def create_upload_token(self, *, workspace_id: str | None = None, **opts: Any) -> APIBlobUploadToken:
        """POST /upload-tokens — short-lived `vcup_` token for browser uploads.

        Options: `path` or `prefix`, `visibility`, `overwrite`, `max_size`, `allowed_extensions`, `cache_control`,
        `content_disposition`, `expires_at`, `metadata`, `expires_in`, `max_uses`.
        """
        if "expires_at" in opts:
            opts["expires_at"] = _iso(opts["expires_at"])
        return self._json("POST", "/upload-tokens", json_body=opts, query=_ws(workspace_id))

    def s3_credentials(self, *, workspace_id: str | None = None) -> APIBlobS3Credentials:
        """GET /s3/credentials — S3-compatible key pair derived from the API key."""
        return self._json("GET", "/s3/credentials", query=_ws(workspace_id))
