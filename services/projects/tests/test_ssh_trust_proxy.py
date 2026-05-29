"""Proxied VM SSH trust setup (Phase 9)."""

from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from helpers import org_admin_token

ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
@respx.mock
async def test_setup_ssh_trust_route(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "SSH", "slug": "ssh-trust-ui"},
    )
    assert project.status_code == 201
    project_id = project.json()["id"]
    agent_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    vm_name = "web-01"

    respx.get(f"http://registry.test/api/v1/internal/agents/{agent_id}/connect").mock(
        return_value=Response(
            200,
            json={
                "agent_id": agent_id,
                "organization_id": ORG_ID,
                "base_url": "https://agent.test",
                "agent_token": "agent-secret",
                "tls_verify": False,
            },
        )
    )
    respx.get(f"https://agent.test/api/v1/vms/{vm_name}").mock(
        return_value=Response(
            200,
            json={"name": vm_name, "status": "on", "libvirt_state": "RUNNING"},
        )
    )

    assigned = await client.post(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/assignments",
        headers=headers,
        json={"resource_type": "vm", "name": vm_name},
    )
    assert assigned.status_code == 201, assigned.text
    respx.get(f"http://iam.test/api/v1/organizations/{ORG_ID}/ssh/ca").mock(
        return_value=Response(
            200,
            json={
                "organization_id": ORG_ID,
                "public_key_openssh": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItestca huy-ssh-ca",
            },
        )
    )
    respx.put(f"https://agent.test/api/v1/vms/{vm_name}/ssh-trust").mock(
        return_value=Response(
            200,
            json={"vm_name": vm_name, "cloud_config_snippet": "#cloud-config\nssh:\n  ca_keys: []\n"},
        )
    )

    r = await client.post(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/vms/{vm_name}/ssh-trust/setup",
        headers=headers,
        json={"linux_username": "ubuntu"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["vm_name"] == vm_name


@pytest.mark.asyncio
@respx.mock
async def test_guest_onboard_bundle(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "SSH", "slug": "ssh-onboard"},
    )
    project_id = project.json()["id"]
    agent_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    vm_name = "legacy-01"

    respx.get(f"http://registry.test/api/v1/internal/agents/{agent_id}/connect").mock(
        return_value=Response(
            200,
            json={
                "agent_id": agent_id,
                "organization_id": ORG_ID,
                "base_url": "https://agent.test",
                "agent_token": "agent-secret",
                "tls_verify": False,
            },
        )
    )
    respx.get(f"https://agent.test/api/v1/vms/{vm_name}").mock(
        return_value=Response(
            200,
            json={"name": vm_name, "status": "on", "libvirt_state": "RUNNING"},
        )
    )

    assigned = await client.post(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/assignments",
        headers=headers,
        json={"resource_type": "vm", "name": vm_name},
    )
    assert assigned.status_code == 201, assigned.text

    respx.get(f"http://iam.test/api/v1/organizations/{ORG_ID}/ssh/ca").mock(
        return_value=Response(
            200,
            json={
                "organization_id": ORG_ID,
                "public_key_openssh": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItestca huy-ssh-ca",
            },
        )
    )
    respx.get(f"http://iam.test/api/v1/organizations/{ORG_ID}/ssh/account-mappings").mock(
        return_value=Response(200, json=[])
    )

    r = await client.get(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/vms/{vm_name}/guest-onboard",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["filename"] == f"huy-ssh-onboard-{vm_name}.sh"
    assert "TrustedUserCAKeys" in body["script"] or "huy-org-ca.pem" in body["script"]
    assert "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItestca" in body["script"]
