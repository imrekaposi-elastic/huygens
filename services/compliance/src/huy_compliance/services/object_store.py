"""Object store abstraction for evidence and exports.

Phase 7+ supports a local store and S3-compatible stores (MinIO).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException

from huy_compliance.config import Settings


@dataclass(frozen=True)
class ObjectRef:
    key: str
    size_bytes: int | None = None


class ObjectStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def put_bytes(self, *, key: str, data: bytes) -> ObjectRef:
        if self._settings.object_store_kind == "local":
            base = Path(self._settings.object_store_local_dir).resolve()
            path = base / key
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_suffix(path.suffix + ".tmp")
            tmp_path.write_bytes(data)
            os.replace(tmp_path, path)
            return ObjectRef(key=key, size_bytes=len(data))
        if self._settings.object_store_kind == "s3":
            bucket = self._settings.object_store_bucket
            if not bucket:
                raise HTTPException(status_code=500, detail="OBJECT_STORE_BUCKET is required for s3")
            client = _s3_client(self._settings)
            client.put_object(Bucket=bucket, Key=key, Body=data)
            return ObjectRef(key=key, size_bytes=len(data))
        raise HTTPException(status_code=500, detail="Unknown OBJECT_STORE_KIND")

    def delete(self, *, key: str) -> None:
        if self._settings.object_store_kind == "local":
            base = Path(self._settings.object_store_local_dir).resolve()
            path = base / key
            # Best-effort: object might already be gone; DB is the source of truth.
            try:
                path.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                # Don't block DB deletion on filesystem quirks in dev.
                return
            return
        if self._settings.object_store_kind == "s3":
            bucket = self._settings.object_store_bucket
            if not bucket:
                raise HTTPException(status_code=500, detail="OBJECT_STORE_BUCKET is required for s3")
            client = _s3_client(self._settings)
            try:
                client.delete_object(Bucket=bucket, Key=key)
            except Exception:  # noqa: BLE001
                # Best-effort; S3 delete is idempotent.
                return
            return
        raise HTTPException(status_code=500, detail="Unknown OBJECT_STORE_KIND")

    def get_path(self, *, key: str) -> Path:
        if self._settings.object_store_kind != "local":
            raise HTTPException(status_code=400, detail="Path access only supported for local object store")
        base = Path(self._settings.object_store_local_dir).resolve()
        path = base / key
        if not path.exists():
            raise HTTPException(status_code=404, detail="Object not found")
        return path

    def get_presigned_download_url(self, *, key: str, expires_seconds: int = 300) -> str:
        if self._settings.object_store_kind != "s3":
            raise HTTPException(
                status_code=400, detail="Presigned URLs only supported for s3 object store"
            )
        bucket = self._settings.object_store_bucket
        if not bucket:
            raise HTTPException(status_code=500, detail="OBJECT_STORE_BUCKET is required for s3")
        client = _s3_client(self._settings)
        return client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )

    def stream_bytes(self, *, key: str, chunk_size: int = 1024 * 1024) -> tuple[Iterable[bytes], int | None]:
        """Stream object bytes from the backing store.

        For s3 mode, this reads via server-side credentials so buckets can remain private and
        endpoints can stay internal-only.
        """
        if self._settings.object_store_kind != "s3":
            raise HTTPException(status_code=400, detail="Streaming is only supported for s3 object store")
        bucket = self._settings.object_store_bucket
        if not bucket:
            raise HTTPException(status_code=500, detail="OBJECT_STORE_BUCKET is required for s3")
        client = _s3_client(self._settings)
        try:
            res = client.get_object(Bucket=bucket, Key=key)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=404, detail="Object not found") from exc

        length = res.get("ContentLength")
        body = res["Body"]

        def gen() -> Iterable[bytes]:
            for chunk in body.iter_chunks(chunk_size=chunk_size):
                if chunk:
                    yield chunk

        return gen(), int(length) if length is not None else None


def _s3_client(settings: Settings):
    try:
        import boto3
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500, detail="boto3 is required for OBJECT_STORE_KIND=s3"
        ) from exc
    return boto3.client(
        "s3",
        endpoint_url=settings.object_store_endpoint,
        region_name=settings.object_store_region,
        aws_access_key_id=settings.object_store_access_key_id,
        aws_secret_access_key=settings.object_store_secret_access_key,
    )

