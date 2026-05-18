"""Base image download, cache, and per-VM overlay disks."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import httpx
import structlog

logger = structlog.get_logger(__name__)

_STREAM_CHUNK_SIZE = 1024 * 1024  # 1 MiB


class ImageStore:
    def __init__(self, images_dir: Path, download_timeout: int = 600) -> None:
        self._images_dir = images_dir
        self._images_dir.mkdir(parents=True, exist_ok=True)
        self._timeout = download_timeout

    def _cache_key(self, image_ref: str) -> str:
        return hashlib.sha256(image_ref.encode()).hexdigest()[:16]

    @staticmethod
    def verify_sha256(path: Path, expected: str) -> None:
        digest = ImageStore._sha256_file(path)
        if digest.lower() != expected.lower():
            raise ValueError(f"SHA-256 mismatch: expected {expected}, got {digest}")

    @staticmethod
    def _sha256_file(path: Path, chunk_size: int = _STREAM_CHUNK_SIZE) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    def download_url_to_path(
        self, url: str, dest: Path, expected_sha256: str | None = None
    ) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(".part")
        logger.info("downloading_image", url=url, dest=str(dest))
        timeout = httpx.Timeout(self._timeout, connect=60.0)
        hasher = hashlib.sha256() if expected_sha256 else None
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                with client.stream("GET", url) as resp:
                    resp.raise_for_status()
                    with tmp.open("wb") as handle:
                        for chunk in resp.iter_bytes(chunk_size=_STREAM_CHUNK_SIZE):
                            if not chunk:
                                continue
                            if hasher is not None:
                                hasher.update(chunk)
                            handle.write(chunk)
            if expected_sha256 and hasher is not None:
                digest = hasher.hexdigest()
                if digest.lower() != expected_sha256.lower():
                    raise ValueError(
                        f"SHA-256 mismatch: expected {expected_sha256}, got {digest}"
                    )
            tmp.rename(dest)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        return dest

    def resolve_base_image(self, image_ref: str) -> Path:
        """Resolve URL, local path, or managed image name to a readable image file."""
        parsed = urlparse(image_ref)
        if parsed.scheme in ("http", "https"):
            key = self._cache_key(image_ref)
            dest = self._images_dir / f"{key}.qcow2"
            if dest.exists():
                return dest
            return self.download_url_to_path(image_ref, dest)
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
