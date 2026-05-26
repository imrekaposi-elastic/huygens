"""Path safety helpers for image import."""

from __future__ import annotations

from pathlib import Path

import pytest

from huy_libvirt_agent.services.path_safety import (
    PathSafetyError,
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
