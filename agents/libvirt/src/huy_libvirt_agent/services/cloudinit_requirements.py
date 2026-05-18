"""Check that cloud-init is available for schema validation."""

from __future__ import annotations

import shutil


def cloud_init_schema_available() -> bool:
    if shutil.which("cloud-init"):
        return True
    try:
        import cloudinit.config.schema  # noqa: F401

        return True
    except ImportError:
        return False


def assert_cloud_init_available() -> None:
    if not cloud_init_schema_available():
        raise RuntimeError(
            "cloud-init is required but not installed. Install the OS package "
            "(see agents/libvirt/requirements-host.txt) or set "
            "HUY_CLOUD_INIT_VALIDATION=basic"
        )
