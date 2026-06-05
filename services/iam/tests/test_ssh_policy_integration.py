"""SSH policy API and internal authorization integration tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from conftest import login

SERVICE_HEADERS = {"X-Huy-Service-Token": "test-ssh-gateway-service-token"}


async def _org_setup(client: AsyncClient) -> tuple[str, str, str]:
    pa_token = await login(client, "platform-admin", "platform-admin-secret-12")
    pa_headers = {"Authorization": f"Bearer {pa_token}"}
    org = await client.post(
        "/api/v1/organizations",
        headers=pa_headers,
        json={"name": "SSH Org", "slug": "ssh-org"},
    )
    assert org.status_code == 201, org.text
    org_id = org.json()["id"]
    user = await client.post(
        f"/api/v1/organizations/{org_id}/users",
        headers=pa_headers,
        json={
            "email": "ssh@example.com",
            "username": "ssh-user",
            "password": "ssh-user-secret-12",
            "org_roles": ["admin"],
        },
    )
    assert user.status_code == 201, user.text
    user_id = user.json()["id"]
    org_token = await login(client, "ssh-user", "ssh-user-secret-12")
    return org_id, user_id, org_token


@pytest.mark.asyncio
async def test_ssh_ca_and_guest_onboard(client: AsyncClient) -> None:
    org_id, _user_id, org_token = await _org_setup(client)
    headers = {"Authorization": f"Bearer {org_token}"}

    ca = await client.get(f"/api/v1/organizations/{org_id}/ssh/ca", headers=headers)
    assert ca.status_code == 200, ca.text
    assert ca.json()["public_key_openssh"].startswith("ssh-")

    bundle = await client.get(
        f"/api/v1/organizations/{org_id}/ssh/guest-onboard",
        headers=headers,
        params={"vm_name": "web-01"},
    )
    assert bundle.status_code == 200, bundle.text
    assert "script" in bundle.json()
    assert bundle.json()["linux_username"] == "huygens"


@pytest.mark.asyncio
async def test_ssh_policy_crud(client: AsyncClient) -> None:
    org_id, user_id, org_token = await _org_setup(client)
    headers = {"Authorization": f"Bearer {org_token}"}
    base = f"/api/v1/organizations/{org_id}/ssh"

    mapping = await client.post(
        f"{base}/account-mappings",
        headers=headers,
        json={
            "user_id": user_id,
            "linux_username": "huygens",
            "default_shell": "/bin/bash",
            "auto_provision": True,
        },
    )
    assert mapping.status_code == 201, mapping.text
    mapping_id = mapping.json()["id"]

    listed = await client.get(f"{base}/account-mappings", headers=headers)
    assert listed.status_code == 200
    assert any(m["id"] == mapping_id for m in listed.json())

    group = await client.post(
        f"{base}/access-groups",
        headers=headers,
        json={"name": "ops", "description": "Operators"},
    )
    assert group.status_code == 201, group.text
    group_id = group.json()["id"]

    member = await client.post(
        f"{base}/access-groups/{group_id}/members",
        headers=headers,
        json={"user_id": user_id},
    )
    assert member.status_code == 204

    rule = await client.post(
        f"{base}/sudo-rules",
        headers=headers,
        json={
            "name": "restart",
            "command_allow_list": ["/bin/systemctl restart *"],
            "allow_root": False,
        },
    )
    assert rule.status_code == 201, rule.text
    rule_id = rule.json()["id"]

    bind = await client.post(
        f"{base}/sudo-rules/{rule_id}/groups",
        headers=headers,
        json={"group_id": group_id},
    )
    assert bind.status_code == 204

    rules = await client.get(f"{base}/sudo-rules", headers=headers)
    assert rules.status_code == 200
    assert any(r["id"] == rule_id for r in rules.json())

    deleted = await client.delete(f"{base}/account-mappings/{mapping_id}", headers=headers)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_internal_authorize_and_policy_snapshot(client: AsyncClient) -> None:
    org_id, user_id, org_token = await _org_setup(client)
    headers = {"Authorization": f"Bearer {org_token}"}
    project_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    await client.post(
        f"/api/v1/organizations/{org_id}/ssh/account-mappings",
        headers=headers,
        json={"user_id": user_id, "linux_username": "huygens"},
    )

    denied = await client.post(
        "/internal/v1/ssh/authorize",
        headers=SERVICE_HEADERS,
        json={
            "organization_id": org_id,
            "project_id": project_id,
            "vm_name": "web-01",
            "vm_assigned_to_project": False,
            "user_id": user_id,
            "user_username": "ssh-user",
            "org_memberships": [{"organization_id": org_id, "roles": ["admin"]}],
            "project_roles": [],
        },
    )
    assert denied.status_code == 200
    assert denied.json()["allowed"] is False
    assert denied.json()["reason"] == "vm_not_in_project"

    allowed = await client.post(
        "/internal/v1/ssh/authorize",
        headers=SERVICE_HEADERS,
        json={
            "organization_id": org_id,
            "project_id": project_id,
            "vm_name": "web-01",
            "vm_assigned_to_project": True,
            "user_id": user_id,
            "user_username": "ssh-user",
            "org_memberships": [{"organization_id": org_id, "roles": ["admin"]}],
            "project_roles": [],
        },
    )
    assert allowed.status_code == 200, allowed.text
    body = allowed.json()
    assert body["allowed"] is True
    assert body["linux_username"] == "huygens"
    assert body["ca_public_key"].startswith("ssh-")

    snapshot = await client.get(
        f"/internal/v1/ssh/policy-snapshot/{org_id}",
        headers=SERVICE_HEADERS,
    )
    assert snapshot.status_code == 200, snapshot.text
    snap = snapshot.json()
    assert snap["ca_public_key_openssh"].startswith("ssh-")
    assert len(snap["mappings"]) >= 1


@pytest.mark.asyncio
async def test_internal_service_token_rejected(client: AsyncClient) -> None:
    r = await client.get(
        "/internal/v1/ssh/policy-snapshot/11111111-1111-1111-1111-111111111111",
        headers={"X-Huy-Service-Token": "wrong"},
    )
    assert r.status_code == 401
