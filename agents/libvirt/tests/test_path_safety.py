"""Path safety helpers for image import."""

from __future__ import annotations

from pathlib import Path

import pytest

from huy_libvirt_agent.services.path_safety import (
    PathSafetyError,
    copy_validated_local_image,
    resolve_cached_disk_path,
    resolve_local_image_source,
)


def test_rejects_path_outside_allowed_roots(tmp_path: Path) -> None:
    outside = tmp_path / "outside.qcow2"
    outside.write_bytes(b"x")
    allowed = [tmp_path / "images" / "import"]
    allowed[0].mkdir(parents=True)
    with pytest.raises(PathSafetyError):
        resolve_local_image_source(str(outside), allowed)


def test_allows_file_under_allowed_root(tmp_path: Path) -> None:
    root = tmp_path / "images" / "import"
    root.mkdir(parents=True)
    disk = root / "base.qcow2"
    disk.write_bytes(b"x")
    resolved = resolve_local_image_source(str(disk), [root])
    assert resolved == disk.resolve()


def test_copy_validated_local_image(tmp_path: Path) -> None:
    root = tmp_path / "images" / "import"
    root.mkdir(parents=True)
    disk = root / "base.qcow2"
    disk.write_bytes(b"payload")
    dest = tmp_path / "images" / "registry" / "img" / "disk.qcow2"
    dest.parent.mkdir(parents=True)
    copy_validated_local_image(str(disk), dest, [root])
    assert dest.read_bytes() == b"payload"


def test_resolve_cached_disk_path_rejects_mismatch(tmp_path: Path) -> None:
    registry = tmp_path / "registry"
    image_dir = registry / "img"
    image_dir.mkdir(parents=True)
    disk = image_dir / "disk.qcow2"
    disk.write_bytes(b"x")
    with pytest.raises(PathSafetyError):
        resolve_cached_disk_path(str(tmp_path / "other.qcow2"), registry, "img")


def test_rejects_unsafe_child_name(tmp_path: Path) -> None:
    from huy_libvirt_agent.services.path_safety import safe_child_dir

    parent = tmp_path / "vnets"
    parent.mkdir()
    with pytest.raises(PathSafetyError):
        safe_child_dir(parent, "../escape")
