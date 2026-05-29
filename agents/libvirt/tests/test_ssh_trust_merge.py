"""Tests for SSH trust cloud-init merge."""

from huy_libvirt_agent.services.ssh_trust import build_ssh_trust_cloud_config, merge_cloud_config_user_data


def test_merge_cloud_config_adds_ca_and_user() -> None:
    base = """#cloud-config
users:
  - name: ubuntu
    shell: /bin/bash
"""
    overlay = build_ssh_trust_cloud_config(
        ca_public_key_openssh="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI test",
        linux_username="huygens",
        sudoers_lines=[],
    )
    merged = merge_cloud_config_user_data(base, overlay)
    assert "huygens" in merged
    assert "ca_keys" in merged
    assert "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI test" in merged
    assert "ubuntu" in merged
    assert "ssh_pwauth: false" in merged
