"""Cloud-init validation tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from huy_libvirt_agent.services.cloudinit_validator import (
    CloudInitPayload,
    CloudInitValidationError,
    CloudInitValidator,
)


def test_rejects_missing_cloud_config_header() -> None:
    v = CloudInitValidator("basic")
    with pytest.raises(CloudInitValidationError) as exc:
        v.validate(
            CloudInitPayload(
                user_data="users:\n  - name: ubuntu\n",
                meta_data="instance-id: x\n",
            )
        )
    assert exc.value.issues[0].field == "user_data"
    assert "header" in exc.value.issues[0].message.lower()


def test_rejects_invalid_yaml() -> None:
    v = CloudInitValidator("basic")
    with pytest.raises(CloudInitValidationError) as exc:
        v.validate(
            CloudInitPayload(
                user_data="#cloud-config\nusers:\n  - name: ubuntu\n    sudo: [ALL=(ALL)",
                meta_data="instance-id: x\n",
            )
        )
    assert any(i.field == "user_data" for i in exc.value.issues)


def test_rejects_network_config_without_version() -> None:
    v = CloudInitValidator("basic")
    with pytest.raises(CloudInitValidationError):
        v.validate(
            CloudInitPayload(
                user_data="#cloud-config\nssh_pwauth: false\n",
                meta_data="instance-id: x\n",
                network_config="ethernets:\n  eth0:\n    dhcp4: true\n",
            )
        )


def test_accepts_valid_minimal_config() -> None:
    v = CloudInitValidator("basic")
    v.validate(
        CloudInitPayload(
            user_data="#cloud-config\nssh_pwauth: false\n",
            meta_data="instance-id: x\nlocal-hostname: x\n",
            network_config="version: 2\nethernets:\n  eth0:\n    dhcp4: true\n",
            ssh_keys=["ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI test@example.com"],
        )
    )


def test_validate_endpoint_rejects_bad_config(
    client: TestClient, auth_headers: dict
) -> None:
    resp = client.post(
        "/api/v1/cloud-init/validate",
        headers=auth_headers,
        json={
            "user_data": "not-a-header\nfoo: bar\n",
            "meta_data": "instance-id: x\n",
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "CLOUD_INIT_INVALID"
    assert len(body["issues"]) >= 1


def test_validate_endpoint_accepts_good_config(
    client: TestClient, auth_headers: dict
) -> None:
    resp = client.post(
        "/api/v1/cloud-init/validate",
        headers=auth_headers,
        json={
            "user_data": "#cloud-config\nssh_pwauth: false\n",
            "meta_data": "instance-id: x\n",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is True


def test_profile_create_rejects_invalid(
    client: TestClient, auth_headers: dict
) -> None:
    resp = client.post(
        "/api/v1/cloud-init",
        headers=auth_headers,
        json={
            "name": "bad-profile",
            "user_data": "missing-header: true\n",
            "meta_data": "instance-id: x\n",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "CLOUD_INIT_INVALID"


def test_validation_off_skips_checks() -> None:
    v = CloudInitValidator("off")
    v.validate(CloudInitPayload(user_data="totally invalid", meta_data=""))
