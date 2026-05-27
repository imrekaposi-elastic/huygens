"""Filesystem path validation for agent services (CodeQL path-injection guards)."""

from __future__ import annotations

import re
import shutil
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


def _resolved_under_allowed_roots(resolved: Path, allowed_roots: list[Path]) -> bool:
    roots = [r.resolve() for r in allowed_roots]
    return any(_is_under_root(resolved, root) for root in roots)


def resolve_local_image_source(source: str, allowed_roots: list[Path]) -> Path:
    """
    Resolve a local disk image path for copy/import.

    Rejects relative paths, traversal outside allowed roots, and non-files.
    """
    if not source or "\0" in source:
        raise PathSafetyError("Invalid local image path")
    candidate = Path(source)
    if not candidate.is_absolute():
        raise PathSafetyError("Local image source must be an absolute path")

    resolved = candidate.resolve()
    if not _resolved_under_allowed_roots(resolved, allowed_roots):
        allowed = ", ".join(str(r.resolve()) for r in allowed_roots)
        raise PathSafetyError(
            f"Local image path must be under an allowed directory ({allowed})"
        )
    if not resolved.is_file():
        raise FileNotFoundError(f"Source not found: {source}")
    return resolved


def copy_validated_local_image(source: str, dest: Path, allowed_roots: list[Path]) -> None:
    """Copy a validated local image file into dest (no-op when source and dest are the same)."""
    validated_src = resolve_local_image_source(source, allowed_roots)
    dest_resolved = dest.resolve()
    if validated_src == dest_resolved:
        return
    if not validated_src.is_file():
        raise FileNotFoundError(f"Source not found: {source}")
    dest_resolved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(validated_src, dest_resolved)


def resolve_cached_disk_path(cached_path: str, registry_dir: Path, image_name: str) -> Path:
    """Ensure metadata cached_path points inside this image's registry directory."""
    safe_registry_name(image_name)

    expected = (registry_dir / image_name / "disk.qcow2").resolve()
    if Path(cached_path).resolve() != expected:
        raise PathSafetyError("Cached image path does not match expected location")
    if not expected.is_file():
        raise PathSafetyError("Cached image file missing")
    return expected
