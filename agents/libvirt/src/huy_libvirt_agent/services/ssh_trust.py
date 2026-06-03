"""Cloud-init fragments for Huygens SSH CA trust and sudoers."""

from __future__ import annotations

import yaml

# Match shared/huy_ssh_onboard and guest onboard script paths.
SSH_CA_PEM_PATH = "/etc/ssh/huy-org-ca.pem"
SSH_CA_SSHD_DROPIN_PATH = "/etc/ssh/sshd_config.d/99-huy-org-ca.conf"
SSH_CA_RELOAD_CMD = (
    "systemctl try-reload-or-restart ssh || systemctl try-reload-or-restart sshd || true"
)


def build_ssh_trust_cloud_config(
    *,
    ca_public_key_openssh: str,
    linux_username: str,
    sudoers_lines: list[str],
    default_shell: str = "/bin/bash",
) -> str:
    """Return a #cloud-config snippet for VM SSH trust bootstrap.

    Uses write_files + runcmd (cloud-init schema) instead of ssh.ca_keys, which strict
    schema validation rejects.
    """
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
"""
    ca_line = ca_public_key_openssh.strip()
    trust_files = f"""  - path: {SSH_CA_PEM_PATH}
    permissions: '0644'
    content: |
      {ca_line}
  - path: {SSH_CA_SSHD_DROPIN_PATH}
    permissions: '0644'
    content: |
      TrustedUserCAKeys {SSH_CA_PEM_PATH}
"""
    if sudo_block:
        files_block = sudo_block.rstrip() + "\n" + trust_files
    else:
        files_block = "write_files:\n" + trust_files

    return f"""#cloud-config
{users_block}{files_block}ssh_pwauth: false
runcmd:
  - {SSH_CA_RELOAD_CMD}
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


def _merge_runcmd(base_doc: dict, overlay_doc: dict) -> None:
    base_cmds = list(base_doc.get("runcmd") or [])
    overlay_cmds = overlay_doc.get("runcmd")
    if not overlay_cmds:
        return
    if isinstance(overlay_cmds, str):
        overlay_cmds = [overlay_cmds]
    if not isinstance(overlay_cmds, list):
        return
    for cmd in overlay_cmds:
        if cmd not in base_cmds:
            base_cmds.append(cmd)
    base_doc["runcmd"] = base_cmds


def merge_cloud_config_user_data(base: str, overlay: str) -> str:
    """Merge overlay #cloud-config into base (users, SSH CA files, write_files, runcmd)."""
    base_doc = _parse_cloud_config(base)
    overlay_doc = _parse_cloud_config(overlay)

    base_users: dict[str, dict] = {}
    for entry in base_doc.get("users") or []:
        if isinstance(entry, dict) and entry.get("name"):
            base_users[str(entry["name"])] = dict(entry)
    for entry in overlay_doc.get("users") or []:
        if isinstance(entry, dict) and entry.get("name"):
            name = str(entry["name"])
            merged_user = {**base_users.get(name, {}), **entry}
            # Empty ssh_authorized_keys breaks schema validation; drop when unused.
            if merged_user.get("ssh_authorized_keys") == []:
                merged_user.pop("ssh_authorized_keys", None)
            base_users[name] = merged_user
    if base_users:
        base_doc["users"] = list(base_users.values())

    # Legacy overlays may still use ssh.ca_keys — fold into write_files when present.
    overlay_ssh = overlay_doc.get("ssh") or {}
    if isinstance(overlay_ssh, dict) and overlay_ssh.get("ca_keys"):
        ca_keys = overlay_ssh["ca_keys"]
        if isinstance(ca_keys, list) and ca_keys:
            legacy = build_ssh_trust_cloud_config(
                ca_public_key_openssh=str(ca_keys[0]),
                linux_username="huygens",
                sudoers_lines=[],
            )
            overlay_doc = _parse_cloud_config(legacy)

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

    _merge_runcmd(base_doc, overlay_doc)

    # Do not carry ssh: {ca_keys: ...} into merged output (invalid under strict schema).
    base_doc.pop("ssh", None)

    merged = yaml.dump(base_doc, default_flow_style=False, sort_keys=False).rstrip()
    return f"#cloud-config\n{merged}\n"
