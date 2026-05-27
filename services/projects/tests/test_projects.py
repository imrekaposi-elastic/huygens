"""Project CRUD tests."""

from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from helpers import auditor_token, operator_token, org_admin_token, platform_token

ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
async def test_create_and_list_projects(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    created = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "organization_id": ORG_ID,
            "name": "Lab",
            "slug": "lab",
            "description": "Dev workloads",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["slug"] == "lab"
    assert body["organization_id"] == ORG_ID

    listed = await client.get("/api/v1/projects", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_auditor_cannot_create_project(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {platform_token()}"}
    created = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "X", "slug": "x"},
    )
    project_id = created.json()["id"]

    auditor_headers = {"Authorization": f"Bearer {auditor_token(ORG_ID, project_id)}"}
    denied = await client.post(
        "/api/v1/projects",
        headers=auditor_headers,
        json={"organization_id": ORG_ID, "name": "Y", "slug": "y"},
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
@respx.mock
async def test_list_project_agents(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Lab", "slug": "lab2"},
    )
    project_id = project.json()["id"]

    respx.get("http://registry.test/api/v1/internal/agent-technologies").mock(
        return_value=Response(
            200,
            json=[
                {
                    "id": "tech-1",
                    "slug": "libvirt-agent",
                    "name": "Libvirt agent",
                    "description": None,
                    "platform_enabled": True,
                }
            ],
        )
    )
    await client.put(
        f"/api/v1/projects/{project_id}/agent-technologies",
        headers=headers,
        json={"technologies": [{"agent_technology_id": "tech-1", "enabled": True}]},
    )

    respx.get("http://registry.test/api/v1/agents").mock(
        return_value=Response(
            200,
            json=[
                {
                    "id": "agent-1",
                    "name": "dommel",
                    "base_url": "https://dommel:8765",
                    "organization_id": ORG_ID,
                    "agent_technology_id": "tech-1",
                    "agent_technology_slug": "libvirt-agent",
                    "connection_status": "connected",
                },
                {
                    "id": "agent-2",
                    "name": "other-org",
                    "base_url": "https://other:8765",
                    "organization_id": "22222222-2222-2222-2222-222222222222",
                    "connection_status": "pending",
                },
            ],
        )
    )

    agents = await client.get(f"/api/v1/projects/{project_id}/agents", headers=headers)
    assert agents.status_code == 200
    data = agents.json()
    assert len(data) == 1
    assert data[0]["name"] == "dommel"


@pytest.mark.asyncio
@respx.mock
async def test_operator_can_proxy_list_vms(client: AsyncClient) -> None:
    admin_headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=admin_headers,
        json={"organization_id": ORG_ID, "name": "Ops", "slug": "ops"},
    )
    project_id = project.json()["id"]
    agent_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

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
    respx.get("https://agent.test/api/v1/vms").mock(
        return_value=Response(200, json=[{"name": "web-01", "status": "on"}])
    )
    respx.post("https://agent.test/api/v1/vms").mock(
        return_value=Response(201, json={"name": "web-01", "status": "on"})
    )

    op_headers = {"Authorization": f"Bearer {operator_token(ORG_ID, project_id)}"}
    created = await client.post(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/vms",
        headers=op_headers,
        json={"name": "web-01", "vcpu": 1, "memory_mb": 512},
    )
    assert created.status_code == 201

    vms = await client.get(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/vms",
        headers=op_headers,
    )
    assert vms.status_code == 200
    assert vms.json()[0]["name"] == "web-01"


@pytest.mark.asyncio
@respx.mock
async def test_auditor_cannot_delete_vm(client: AsyncClient) -> None:
    admin_headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=admin_headers,
        json={"organization_id": ORG_ID, "name": "Audit", "slug": "audit"},
    )
    project_id = project.json()["id"]
    agent_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    auditor_headers = {"Authorization": f"Bearer {auditor_token(ORG_ID, project_id)}"}
    denied = await client.delete(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/vms/web-01",
        headers=auditor_headers,
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
@respx.mock
async def test_reject_delete_readonly_default_network(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Net", "slug": "net"},
    )
    project_id = project.json()["id"]
    agent_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"

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

    denied = await client.delete(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/networks/default",
        headers=headers,
    )
    assert denied.status_code == 403
    assert "readonly" in denied.json()["detail"].lower()


@pytest.mark.asyncio
@respx.mock
async def test_reject_delete_readonly_network_by_flag(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Net2", "slug": "net2"},
    )
    project_id = project.json()["id"]
    agent_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"

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
    respx.get("https://agent.test/api/v1/networks/system").mock(
        return_value=Response(
            200,
            json={
                "name": "system",
                "readonly": True,
                "deletable": False,
                "active": True,
                "labels": {},
            },
        )
    )

    denied = await client.delete(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/networks/system",
        headers=headers,
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
@respx.mock
async def test_internal_resource_assignments(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Lab", "slug": "lab-assign"},
    )
    project_id = project.json()["id"]
    agent_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"

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
    respx.post("https://agent.test/api/v1/vms").mock(
        return_value=Response(201, json={"name": "web-01", "status": "on"})
    )

    created = await client.post(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/vms",
        headers=headers,
        json={"name": "web-01", "vcpu": 1, "memory_mb": 512},
    )
    assert created.status_code == 201

    listed = await client.get(
        f"/api/v1/internal/organizations/{ORG_ID}/resource-assignments",
        headers={"X-Huy-Service-Token": "test-inventory-service-token"},
    )
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "web-01"
    assert rows[0]["resource_type"] == "vm"
    assert rows[0]["project_name"] == "Lab"


@pytest.mark.asyncio
@respx.mock
async def test_assign_existing_vm_to_project(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Adopt", "slug": "adopt"},
    )
    project_id = project.json()["id"]
    agent_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"

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
    respx.get("https://agent.test/api/v1/vms/web-01").mock(
        return_value=Response(
            200,
            json={"name": "web-01", "status": "on", "libvirt_state": "RUNNING"},
        )
    )

    assigned = await client.post(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/assignments",
        headers=headers,
        json={"resource_type": "vm", "name": "web-01"},
    )
    assert assigned.status_code == 201, assigned.text
    assert assigned.json()["project_name"] == "Adopt"

    listed = await client.get(
        f"/api/v1/internal/organizations/{ORG_ID}/resource-assignments",
        headers={"X-Huy-Service-Token": "test-inventory-service-token"},
    )
    assert any(r["name"] == "web-01" for r in listed.json())


@pytest.mark.asyncio
@respx.mock
async def test_cannot_assign_system_default_network(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Sys", "slug": "sys-net"},
    )
    project_id = project.json()["id"]
    agent_id = "ffffffff-ffff-ffff-ffff-ffffffffffff"

    denied = await client.post(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/assignments",
        headers=headers,
        json={"resource_type": "network", "name": "default"},
    )
    assert denied.status_code == 400
    assert "system network" in denied.json()["detail"].lower()


@pytest.mark.asyncio
@respx.mock
async def test_vm_not_visible_in_other_project(client: AsyncClient) -> None:
    """VMs assigned to project A must not appear in project B list or get."""
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project_a = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Alpha", "slug": "alpha"},
    )
    project_b = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Beta", "slug": "beta"},
    )
    project_a_id = project_a.json()["id"]
    project_b_id = project_b.json()["id"]
    agent_id = "12121212-1212-1212-1212-121212121212"

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
    respx.get("https://agent.test/api/v1/vms").mock(
        return_value=Response(200, json=[{"name": "shared-vm", "status": "on"}])
    )
    respx.post("https://agent.test/api/v1/vms").mock(
        return_value=Response(201, json={"name": "shared-vm", "status": "on"})
    )

    created = await client.post(
        f"/api/v1/projects/{project_a_id}/agents/{agent_id}/vms",
        headers=headers,
        json={"name": "shared-vm", "vcpu": 1, "memory_mb": 512},
    )
    assert created.status_code == 201

    list_b = await client.get(
        f"/api/v1/projects/{project_b_id}/agents/{agent_id}/vms",
        headers=headers,
    )
    assert list_b.status_code == 200
    assert list_b.json() == []

    get_b = await client.get(
        f"/api/v1/projects/{project_b_id}/agents/{agent_id}/vms/shared-vm",
        headers=headers,
    )
    assert get_b.status_code == 404

    list_a = await client.get(
        f"/api/v1/projects/{project_a_id}/agents/{agent_id}/vms",
        headers=headers,
    )
    assert list_a.status_code == 200
    assert len(list_a.json()) == 1
    assert list_a.json()[0]["name"] == "shared-vm"


@pytest.mark.asyncio
@respx.mock
async def test_delete_network_clears_assignment_when_already_gone_on_agent(
    client: AsyncClient,
) -> None:
    """Project assignment and IPAM must be cleared even if the agent no longer has the vnet."""
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "NetDel", "slug": "net-del"},
    )
    project_id = project.json()["id"]
    agent_id = "99999999-9999-9999-9999-999999999999"

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
    respx.get("https://agent.test/api/v1/networks/lab0").mock(
        return_value=Response(404, json={"detail": "not found"})
    )
    respx.delete("https://agent.test/api/v1/networks/lab0").mock(
        return_value=Response(404, json={"detail": "not found"})
    )

    from huy_projects.db import get_session_factory
    from huy_projects.models import ProjectResource

    factory = get_session_factory()
    async with factory() as session:
        session.add(
            ProjectResource(
                project_id=project_id,
                agent_id=agent_id,
                resource_type="network",
                name="lab0",
                desired_state={"ipv4_cidr": "10.0.0.0/24"},
            )
        )
        await session.commit()

    deleted = await client.delete(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/networks/lab0",
        headers=headers,
    )
    assert deleted.status_code == 204

    async with factory() as session:
        from sqlalchemy import select

        rows = await session.execute(
            select(ProjectResource).where(
                ProjectResource.project_id == project_id,
                ProjectResource.name == "lab0",
            )
        )
        assert rows.scalars().all() == []
