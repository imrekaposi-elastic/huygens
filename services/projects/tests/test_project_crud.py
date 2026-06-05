"""Project update/delete and IPAM allocation listing."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from helpers import ORG_ID, org_admin_token


@pytest.mark.asyncio
async def test_update_and_delete_project(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    created = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Temp", "slug": "temp-crud"},
    )
    assert created.status_code == 201, created.text
    project_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/projects/{project_id}",
        headers=headers,
        json={"name": "Temp Renamed", "description": "Updated"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Temp Renamed"
    assert updated.json()["description"] == "Updated"

    deleted = await client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert deleted.status_code == 204

    missing = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_list_project_allocations(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    pool = await client.post(
        f"/api/v1/organizations/{ORG_ID}/ipam/pools",
        headers=headers,
        json={"name": "alloc-pool", "cidr": "10.91.0.0/24"},
    )
    pool_id = pool.json()["id"]
    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Alloc", "slug": "alloc-proj"},
    )
    project_id = project.json()["id"]
    applied = await client.post(
        f"/api/v1/organizations/{ORG_ID}/ipam/projects/{project_id}/wizard/apply",
        headers=headers,
        json={
            "pool_id": pool_id,
            "subnets": [{"cidr": "10.91.0.0/27", "name": "net-a"}],
        },
    )
    assert applied.status_code == 200

    listed = await client.get(
        f"/api/v1/organizations/{ORG_ID}/ipam/projects/{project_id}/allocations",
        headers=headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["network_name"] == "net-a"
