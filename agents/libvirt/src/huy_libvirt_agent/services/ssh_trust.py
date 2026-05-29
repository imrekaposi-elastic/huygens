"""Cloud-init fragments for Huygens SSH CA trust and sudoers."""

from __future__ import annotations


def build_ssh_trust_cloud_config(
    *,
    ca_public_key_openssh: str,
    linux_username: str,
    sudoers_lines: list[str],
    default_shell: str = "/bin/bash",
) -> str:
    """Return a #cloud-config snippet for VM SSH trust bootstrap."""
    sudo_block = ""
    if sudoers_lines:
        sudo_block = "write_files:\n"
        for i, line in enumerate(sudoers_lines):
            sudo_block += (
                f"  - path: /etc/sudoers.d/huy-{i}\n"
                f"    permissions: '0440'\n"
                f"    content: |\n      {line}\n"
            )
    users_block = f"""users:
  - name: {linux_username}
    shell: {default_shell}
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys: []
"""
    ca_line = ca_public_key_openssh.strip()
    return f"""#cloud-config
{users_block}{sudo_block}ssh_pwauth: false
ssh:
  ca_keys:
    - {ca_line}
"""
