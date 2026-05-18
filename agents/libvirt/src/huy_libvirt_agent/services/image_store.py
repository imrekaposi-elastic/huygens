"""Base image download, cache, and per-VM overlay disks."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import httpx
import structlog

logger = structlog.get_logger(__name__)


class ImageStore:
    def __init__(self, images_dir: Path, download_timeout: int = 600) -> None:
        self._images_dir = images_dir
        self._images_dir.mkdir(parents=True, exist_ok=True)
        self._timeout = download_timeout

    def _cache_key(self, image_ref: str) -> str:
        return hashlib.sha256(image_ref.encode()).hexdigest()[:16]

    def resolve_base_image(self, image_ref: str) -> Path:
        parsed = urlparse(image_ref)
        if parsed.scheme in ("http", "https"):
            key = self._cache_key(image_ref)
            dest = self._images_dir / f"{key}.qcow2"
            if dest.exists():
                return dest
            logger.info("downloading_image", url=image_ref)
            with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                resp = client.get(image_ref)
                resp.raise_for_status()
                tmp = dest.with_suffix(".part")
                tmp.write_bytes(resp.content)
                tmp.rename(dest)
            return dest
        path = Path(image_ref)
        if not path.is_file():
            raise FileNotFoundError(f"Image not found: {image_ref}")
        return path

    def create_overlay(self, base: Path, instance_disk: Path) -> Path:
        instance_disk.parent.mkdir(parents=True, exist_ok=True)
        if instance_disk.exists():
            return instance_disk
        subprocess.run(
            [
                "qemu-img",
                "create",
                "-f",
                "qcow2",
                "-b",
                str(base),
                "-F",
                "qcow2",
                str(instance_disk),
            ],
            check=True,
            capture_output=True,
        )
        return instance_disk
