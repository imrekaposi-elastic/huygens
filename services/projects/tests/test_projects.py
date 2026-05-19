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

    respx.get("http://registry.test/api/v1/agents").mock(
        return_value=Response(
            200,
            json=[
                {
                    "id": "agent-1",
                    "name": "dommel",
                    "base_url": "https://dommel:8765",
                    "organization_id": ORG_ID,
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

    op_headers = {"Authorization": f"Bearer {operator_token(ORG_ID, project_id)}"}
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
