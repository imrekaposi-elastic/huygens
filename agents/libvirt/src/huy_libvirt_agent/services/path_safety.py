"""Filesystem path validation for agent services (CodeQL path-injection guards)."""

from __future__ import annotations

import os
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


def _allowed_roots_realpath(allowed_roots: list[Path]) -> list[str]:
    return [os.path.realpath(str(root)) for root in allowed_roots]


def resolve_local_image_source(
    source: str,
    allowed_roots: list[Path],
    *,
    copy_to: Path | None = None,
) -> str:
    """
    Resolve a local disk image path for copy/import.

    Uses os.path.realpath plus prefix checks (CodeQL path-injection pattern) before any
    filesystem access. Returns the validated absolute path string.

    When copy_to is set, the copy runs in the same guarded block as validation.
    """
    if not source or "\0" in source:
        raise PathSafetyError("Invalid local image path")
    if not os.path.isabs(source):
        raise PathSafetyError("Local image source must be an absolute path")

    resolved = os.path.realpath(source)
    for root_real in _allowed_roots_realpath(allowed_roots):
        if resolved == root_real or resolved.startswith(root_real + os.sep):
            if not os.path.isfile(resolved):
                raise FileNotFoundError(f"Source not found: {source}")
            if copy_to is not None:
                dest_resolved = os.path.realpath(str(copy_to))
                if resolved != dest_resolved:
                    dest_parent = os.path.dirname(dest_resolved)
                    if dest_parent:
                        os.makedirs(dest_parent, exist_ok=True)
                    with open(resolved, "rb") as in_file, open(dest_resolved, "wb") as out_file:
                        shutil.copyfileobj(in_file, out_file)
            return resolved

    allowed = ", ".join(_allowed_roots_realpath(allowed_roots))
    raise PathSafetyError(
        f"Local image path must be under an allowed directory ({allowed})"
    )


def copy_validated_local_image(source: str, dest: Path, allowed_roots: list[Path]) -> None:
    """Copy a validated local image file into dest (no-op when source and dest are the same)."""
    resolve_local_image_source(source, allowed_roots, copy_to=dest)


def resolve_cached_disk_path(cached_path: str, registry_dir: Path, image_name: str) -> Path:
    """Ensure metadata cached_path points inside this image's registry directory."""
    safe_registry_name(image_name)

    expected = os.path.realpath(str((registry_dir / image_name / "disk.qcow2").resolve()))
    resolved = os.path.realpath(cached_path)
    if resolved != expected:
        raise PathSafetyError("Cached image path does not match expected location")
    if not os.path.isfile(expected):
        raise PathSafetyError("Cached image file missing")
    return Path(expected)
