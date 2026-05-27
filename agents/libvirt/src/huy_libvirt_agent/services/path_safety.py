"""Filesystem path validation for agent services (CodeQL path-injection guards)."""

from __future__ import annotations

import os
import re
from pathlib import Path

_REGISTRY_NAME = re.compile(r"^[a-zA-Z0-9._-]+$")


class PathSafetyError(ValueError):
    """Raised when a user-supplied path or name is not allowed."""


def safe_registry_name(name: str) -> str:
    """Image/vnet/VM registry names must be a single path segment."""
    if not _REGISTRY_NAME.fullmatch(name):
        raise PathSafetyError(f"Invalid name: {name!r}")
    return name


def safe_child_dir(parent: Path, name: str) -> Path:
    """Return parent/name after validating name is a single safe segment under parent."""
    safe_registry_name(name)
    root = parent.resolve()
    child = (root / name).resolve()
    if not _is_under_root(child, root):
        raise PathSafetyError(f"Path escapes data directory: {name!r}")
    return child


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
    # Use os.path.realpath for normalization so CodeQL can see the safety check.
    if not os.path.isabs(source):
        raise PathSafetyError("Local image source must be an absolute path")

    resolved = os.path.realpath(source)
    if not os.path.isfile(resolved):
        raise FileNotFoundError(f"Source not found: {source}")

    roots = [os.path.realpath(str(r)) for r in allowed_roots]
    if not any(resolved == root or resolved.startswith(root + os.sep) for root in roots):
        allowed = ", ".join(roots)
        raise PathSafetyError(
            f"Local image path must be under an allowed directory ({allowed})"
        )
    return Path(resolved)


def resolve_cached_disk_path(cached_path: str, registry_dir: Path, image_name: str) -> Path:
    """Ensure metadata cached_path points inside this image's registry directory."""
    safe_registry_name(image_name)

    expected = os.path.realpath(str((registry_dir / image_name / "disk.qcow2").resolve()))
    resolved = os.path.realpath(cached_path)
    if resolved != expected:
        raise PathSafetyError("Cached image path does not match expected location")
    if not os.path.isfile(resolved):
        raise PathSafetyError("Cached image file missing")
    return Path(resolved)
