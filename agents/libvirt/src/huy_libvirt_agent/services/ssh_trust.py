"""Cloud-init fragments for Huygens SSH CA trust and sudoers."""

from __future__ import annotations

import yaml


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


def default_ssh_access_user_data(linux_username: str = "huygens") -> str:
    """Optional base profile without org CA (CA is merged at VM create)."""
    return f"""#cloud-config
users:
  - name: {linux_username}
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
ssh_pwauth: false
"""


def _parse_cloud_config(doc: str) -> dict:
    text = doc.strip()
    if text.startswith("#cloud-config"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
    parsed = yaml.safe_load(text)
    return parsed if isinstance(parsed, dict) else {}


def merge_cloud_config_user_data(base: str, overlay: str) -> str:
    """Merge overlay #cloud-config into base (users, ssh CA keys, write_files)."""
    base_doc = _parse_cloud_config(base)
    overlay_doc = _parse_cloud_config(overlay)

    base_users: dict[str, dict] = {}
    for entry in base_doc.get("users") or []:
        if isinstance(entry, dict) and entry.get("name"):
            base_users[str(entry["name"])] = dict(entry)
    for entry in overlay_doc.get("users") or []:
        if isinstance(entry, dict) and entry.get("name"):
            name = str(entry["name"])
            base_users[name] = {**base_users.get(name, {}), **entry}
    if base_users:
        base_doc["users"] = list(base_users.values())

    base_ssh = dict(base_doc.get("ssh") or {})
    overlay_ssh = overlay_doc.get("ssh") or {}
    if isinstance(overlay_ssh, dict) and overlay_ssh.get("ca_keys"):
        keys = list(base_ssh.get("ca_keys") or [])
        for key in overlay_ssh["ca_keys"]:
            if key not in keys:
                keys.append(key)
        base_ssh["ca_keys"] = keys
        base_doc["ssh"] = base_ssh

    if overlay_doc.get("ssh_pwauth") is False:
        base_doc["ssh_pwauth"] = False

    base_files = list(base_doc.get("write_files") or [])
    overlay_files = overlay_doc.get("write_files") or []
    if overlay_files:
        by_path = {
            str(f.get("path")): f for f in base_files if isinstance(f, dict) and f.get("path")
        }
        for entry in overlay_files:
            if isinstance(entry, dict) and entry.get("path"):
                by_path[str(entry["path"])] = entry
        base_doc["write_files"] = list(by_path.values())

    merged = yaml.dump(base_doc, default_flow_style=False, sort_keys=False).rstrip()
    return f"#cloud-config\n{merged}\n"

