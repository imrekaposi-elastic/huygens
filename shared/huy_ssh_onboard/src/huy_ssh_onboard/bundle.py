"""Render downloadable guest onboarding bundles."""

from __future__ import annotations

import shlex
from importlib.resources import files
from typing import Any


def _load_script_template() -> str:
    return (
        files("huy_ssh_onboard.scripts")
        .joinpath("huy-ssh-onboard.sh")
        .read_text(encoding="utf-8")
    )


def build_guest_onboard_bundle(
    *,
    ca_public_key_openssh: str,
    linux_username: str,
    organization_id: str,
    vm_name: str | None = None,
    project_name: str | None = None,
) -> dict[str, Any]:
    """Return metadata + a self-contained shell script for the guest."""
    ca = ca_public_key_openssh.strip()
    user = linux_username.strip()
    if not ca or not user:
        raise ValueError("ca_public_key_openssh and linux_username are required")

    vm_label = vm_name or "guest"
    filename = f"huy-ssh-onboard-{vm_label}.sh"
    header = f"""#!/usr/bin/env bash
# Huygens guest SSH onboard bundle
# Organization: {organization_id}
# Linux user: {user}
{f"# VM / workload: {vm_name}" if vm_name else "# VM / workload: (any)"}
{f"# Project: {project_name}" if project_name else ""}
# Run on the guest as root:  sudo bash {filename}
#
export HUY_SSH_CA_PUBLIC_KEY={shlex.quote(ca)}
export HUY_LINUX_USER={shlex.quote(user)}

"""
    body = _load_script_template()
    # Skip shebang/comment block from template when embedding (keep logic only)
    if body.startswith("#!/"):
        body = body.split("\n", 1)[1]
    script = header + body.lstrip()

    instructions = (
        "Onboard an existing VM for audited Huygens SSH (any hypervisor):\n"
        "1. Copy this script to the guest (scp, hypervisor console, config management, etc.).\n"
        f"2. On the guest: sudo bash {filename}\n"
        "3. Ensure IAM account mapping maps your Huygens user → "
        f"{user!r}, and project role ssh_access is granted.\n"
        "4. Connect from the console or `huy ssh` — uses IAM-signed certificates, not passwords.\n"
    )
    if vm_name:
        instructions = f"Target workload: {vm_name}\n\n" + instructions

    return {
        "organization_id": organization_id,
        "vm_name": vm_name,
        "project_name": project_name,
        "linux_username": user,
        "ca_public_key_openssh": ca,
        "filename": filename,
        "script": script,
        "instructions": instructions,
    }
