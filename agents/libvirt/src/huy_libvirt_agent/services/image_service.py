"""Managed base image registry (CRUD)."""

from __future__ import annotations

import shutil
from datetime import UTC, datetime
import os
from pathlib import Path
from urllib.parse import urlparse

from huy_libvirt_agent.api.schemas.agent import AgentLabels
from huy_libvirt_agent.api.schemas.image import (
    ImageCreateRequest,
    ImageResponse,
    ImageUpdateRequest,
)
from huy_libvirt_agent.app_state import AppState
from huy_libvirt_agent.services.image_store import ImageStore
from huy_libvirt_agent.services.libvirt_client import LibvirtError
from huy_libvirt_agent.services.metadata import read_metadata, write_metadata
from huy_libvirt_agent.services.path_safety import (
    PathSafetyError,
    resolve_cached_disk_path,
    resolve_local_image_source,
    safe_child_dir,
    safe_registry_name,
)


class ImageService:
    def __init__(self, state: AppState) -> None:
        self._state = state
        self._registry_dir = state.settings.data_dir / "images" / "registry"
        self._registry_dir.mkdir(parents=True, exist_ok=True)
        self._store = ImageStore(
            state.settings.data_dir / "images" / "cache",
            state.settings.image_download_timeout_seconds,
        )

    def _image_dir(self, name: str) -> Path:
        return safe_child_dir(self._registry_dir, name)

    def _local_import_roots(self) -> list[Path]:
        data = self._state.settings.data_dir
        roots = [
            data / "images" / "import",
            data / "images" / "cache",
            self._registry_dir,
            Path("/var/lib/libvirt/images"),
        ]
        roots.extend(self._state.settings.image_import_roots)
        return roots

    def _meta_path(self, name: str) -> Path:
        return self._image_dir(name) / "metadata.json"

    def _disk_path(self, name: str) -> Path:
        return self._image_dir(name) / "disk.qcow2"

    def _source_type(self, source: str) -> str:
        if urlparse(source).scheme in ("http", "https"):
            return "url"
        return "path"

    def list_images(self) -> list[ImageResponse]:
        names = [p.name for p in self._registry_dir.iterdir() if p.is_dir()]
        return [self.get_image(n) for n in sorted(names)]

    def get_image(self, name: str) -> ImageResponse:
        meta = read_metadata(self._meta_path(name))
        if not meta:
            raise LibvirtError(f"Image {name} not found", "NOT_FOUND")
        return self._to_response(name, meta)

    def create_image(
        self, body: ImageCreateRequest, correlation_id: str | None = None
    ) -> ImageResponse:
        if self._image_dir(body.name).exists():
            raise LibvirtError(f"Image {body.name} already exists", "IMAGE_EXISTS")
        now = datetime.now(UTC).isoformat()
        labels = self._state.settings.agent_labels
        meta = {
            "labels": labels,
            "source": body.source,
            "source_type": self._source_type(body.source),
            "status": "pending",
            "sha256": body.sha256,
            "created_at": now,
            "updated_at": now,
        }
        self._image_dir(body.name).mkdir(parents=True)
        write_metadata(self._meta_path(body.name), meta)
        if body.fetch:
            meta = self._fetch_into(body.name, meta)
            write_metadata(self._meta_path(body.name), meta)
        self._state.event_bus.publish(
            "huy.image.created",
            f"/hypervisors/{self._state.hostname}",
            {"name": body.name, "labels": labels},
            correlation_id=correlation_id,
        )
        return self._to_response(body.name, meta)

    def update_image(
        self, name: str, body: ImageUpdateRequest, correlation_id: str | None = None
    ) -> ImageResponse:
        meta = read_metadata(self._meta_path(name))
        if not meta:
            raise LibvirtError(f"Image {name} not found", "NOT_FOUND")
        if body.source is not None:
            meta["source"] = body.source
            meta["source_type"] = self._source_type(body.source)
        if body.sha256 is not None:
            meta["sha256"] = body.sha256
        meta["updated_at"] = datetime.now(UTC).isoformat()
        if body.refetch or body.source is not None:
            meta["status"] = "pending"
            write_metadata(self._meta_path(name), meta)
            meta = self._fetch_into(name, meta)
        write_metadata(self._meta_path(name), meta)
        self._state.event_bus.publish(
            "huy.image.updated",
            f"/hypervisors/{self._state.hostname}",
            {"name": name},
            correlation_id=correlation_id,
        )
        return self._to_response(name, meta)

    def delete_image(self, name: str, correlation_id: str | None = None) -> None:
        img_dir = self._image_dir(name)
        if not img_dir.exists():
            raise LibvirtError(f"Image {name} not found", "NOT_FOUND")
        shutil.rmtree(img_dir)
        self._state.event_bus.publish(
            "huy.image.deleted",
            f"/hypervisors/{self._state.hostname}",
            {"name": name},
            correlation_id=correlation_id,
        )

    def resolve_disk_path(self, name: str) -> Path:
        meta = read_metadata(self._meta_path(name))
        if not meta:
            raise LibvirtError(f"Image {name} not found", "NOT_FOUND")
        if meta.get("status") != "ready":
            raise LibvirtError(f"Image {name} is not ready (status={meta.get('status')})", "IMAGE_NOT_READY")
        cached = meta.get("cached_path")
        if cached:
            try:
                return resolve_cached_disk_path(cached, self._registry_dir, name)
            except (PathSafetyError, OSError) as exc:
                raise LibvirtError(f"Image file missing for {name}", "IMAGE_NOT_READY") from exc
        path = self._disk_path(name)
        if not path.is_file():
            raise LibvirtError(f"Image file missing for {name}", "IMAGE_NOT_READY")
        return path

    def _fetch_into(self, name: str, meta: dict) -> dict:
        source = meta["source"]
        dest = self._disk_path(name)
        try:
            if meta["source_type"] == "url":
                self._store.download_url_to_path(source, dest, expected_sha256=meta.get("sha256"))
            else:
                try:
                    src = resolve_local_image_source(source, self._local_import_roots())
                except PathSafetyError as exc:
                    raise LibvirtError(str(exc), "INVALID_SOURCE") from exc
                # Re-check before file copy so CodeQL sees the guard at the sink.
                resolved_src = os.path.realpath(str(src))
                roots = [os.path.realpath(str(r)) for r in self._local_import_roots()]
                if not any(resolved_src == root or resolved_src.startswith(root + os.sep) for root in roots):
                    raise LibvirtError("Local image path must be under an allowed directory", "INVALID_SOURCE")
                if src != dest.resolve():
                    shutil.copy2(src, dest)
                if meta.get("sha256"):
                    self._store.verify_sha256(dest, meta["sha256"])
            meta["status"] = "ready"
            meta["cached_path"] = str(dest)
            meta["size_bytes"] = dest.stat().st_size
            meta["error"] = None
        except Exception as e:
            meta["status"] = "error"
            meta["error"] = str(e)
        meta["updated_at"] = datetime.now(UTC).isoformat()
        return meta

    def _to_response(self, name: str, meta: dict) -> ImageResponse:
        labels = AgentLabels(**meta.get("labels", self._state.settings.agent_labels))
        return ImageResponse(
            name=name,
            labels=labels,
            source=meta["source"],
            source_type=meta["source_type"],
            status=meta.get("status", "pending"),
            cached_path=meta.get("cached_path"),
            size_bytes=meta.get("size_bytes"),
            sha256=meta.get("sha256"),
            error=meta.get("error"),
            created_at=meta["created_at"],
            updated_at=meta["updated_at"],
        )
