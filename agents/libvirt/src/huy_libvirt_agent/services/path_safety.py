"""Filesystem path validation for agent services (CodeQL path-injection guards)."""

from __future__ import annotations

import re
from pathlib import Path

_REGISTRY_NAME = re.compile(r"^[a-zA-Z0-9._-]+$")


class PathSafetyError(ValueError):
    """Raised when a user-supplied path or name is not allowed."""


def safe_registry_name(name: str) -> str:
    """Image/vnet registry names must be a single path segment."""
    if not _REGISTRY_NAME.fullmatch(name):
        raise PathSafetyError(f"Invalid name: {name!r}")
    return name


def _is_under_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_local_image_source(source: str, allowed_roots: list[Path]) -> Path:
    """
    Resolve a local disk image path for copy/import.

    Rejects relative paths, traversal outside allowed roots, and non-files.
    """
    if not source or "\0" in source:
        raise PathSafetyError("Invalid local image path")
    raw = Path(source)
    if not raw.is_absolute():
        raise PathSafetyError("Local image source must be an absolute path")
    resolved = raw.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Source not found: {source}")
    roots = [r.resolve() for r in allowed_roots]
    if not any(_is_under_root(resolved, root) for root in roots):
        allowed = ", ".join(str(r) for r in roots)
        raise PathSafetyError(
            f"Local image path must be under an allowed directory ({allowed})"
        )
    return resolved


def resolve_cached_disk_path(cached_path: str, registry_dir: Path, image_name: str) -> Path:
    """Ensure metadata cached_path points inside this image's registry directory."""
    safe_registry_name(image_name)
    resolved = Path(cached_path).resolve()
    image_dir = (registry_dir / image_name).resolve()
    if not _is_under_root(resolved, image_dir):
        raise PathSafetyError("Cached image path escapes registry directory")
    if not resolved.is_file():
        raise PathSafetyError("Cached image file missing")
    return resolved
