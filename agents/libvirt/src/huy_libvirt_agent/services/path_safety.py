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


def _resolved_under_root(resolved: str, root_real: str) -> bool:
    return resolved == root_real or resolved.startswith(root_real + os.sep)


def _canonical_path_under_root(target_realpath: str, root_real: str) -> str | None:
    """
    Locate target_realpath under root_real by walking the tree.

    Returns a path string produced by the filesystem walk (not the user-supplied path) so
    subsequent open/copy sinks are not fed tainted data.
    """
    for dirpath, _, filenames in os.walk(root_real):
        for name in filenames:
            candidate = os.path.join(dirpath, name)
            if os.path.realpath(candidate) == target_realpath:
                return candidate
    return None


def _match_allowed_root(resolved: str, allowed_roots: list[Path]) -> str | None:
    for root_real in _allowed_roots_realpath(allowed_roots):
        if _resolved_under_root(resolved, root_real):
            return root_real
    return None


def resolve_local_image_source(
    source: str,
    allowed_roots: list[Path],
    *,
    copy_to: Path | None = None,
) -> str:
    """
    Resolve a local disk image path for copy/import.

    User input is only used for comparison. File access uses paths discovered under allowed
    roots via directory enumeration (CodeQL path-injection pattern).
    """
    if not source or "\0" in source:
        raise PathSafetyError("Invalid local image path")
    if not os.path.isabs(source):
        raise PathSafetyError("Local image source must be an absolute path")

    resolved = os.path.realpath(source)
    root_real = _match_allowed_root(resolved, allowed_roots)
    if root_real is None:
        allowed = ", ".join(_allowed_roots_realpath(allowed_roots))
        raise PathSafetyError(
            f"Local image path must be under an allowed directory ({allowed})"
        )

    canonical = _canonical_path_under_root(resolved, root_real)
    if canonical is None:
        raise FileNotFoundError(f"Source not found: {source}")

    if copy_to is not None:
        dest_resolved = os.path.realpath(str(copy_to))
        if canonical != dest_resolved:
            dest_parent = os.path.dirname(dest_resolved)
            if dest_parent:
                os.makedirs(dest_parent, exist_ok=True)
            with open(canonical, "rb") as in_file, open(dest_resolved, "wb") as out_file:
                shutil.copyfileobj(in_file, out_file)

    return canonical


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
