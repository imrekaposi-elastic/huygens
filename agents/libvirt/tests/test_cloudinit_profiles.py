"""Cloud-init profile API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_cloud_init_profile_crud(client: TestClient, auth_headers: dict) -> None:
    create = client.post(
        "/api/v1/cloud-init",
        headers=auth_headers,
        json={
            "name": "default-ssh",
            "user_data": "#cloud-config\nssh_pwauth: false\n",
            "meta_data": "instance-id: template\n",
            "ssh_keys": ["ssh-ed25519 AAAA... test@example"],
        },
    )
    assert create.status_code == 201, create.text
    assert create.json()["name"] == "default-ssh"

    listed = client.get("/api/v1/cloud-init", headers=auth_headers)
    assert listed.status_code == 200
    assert any(p["name"] == "default-ssh" for p in listed.json())

    patch = client.patch(
        "/api/v1/cloud-init/default-ssh",
        headers=auth_headers,
        json={"meta_data": "instance-id: updated\n"},
    )
    assert patch.status_code == 200
    assert "updated" in patch.json()["meta_data"]

    dup = client.post(
        "/api/v1/cloud-init",
        headers=auth_headers,
        json={"name": "default-ssh", "user_data": "#cloud-config\n"},
    )
    assert dup.status_code == 409

    deleted = client.delete("/api/v1/cloud-init/default-ssh", headers=auth_headers)
    assert deleted.status_code == 204

    missing = client.get("/api/v1/cloud-init/default-ssh", headers=auth_headers)
    assert missing.status_code == 404
