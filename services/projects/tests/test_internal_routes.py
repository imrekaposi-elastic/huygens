"""Projects internal API tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from helpers import ORG_ID, org_admin_token


@pytest.mark.asyncio
async def test_internal_list_projects_and_assignments(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    service = {"X-Huy-Service-Token": "test-projects-service-token"}

    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "Internal", "slug": "internal"},
    )
    assert project.status_code == 201, project.text
    project_id = project.json()["id"]

    listed = await client.get(
        f"/api/v1/internal/organizations/{ORG_ID}/projects",
        headers=service,
    )
    assert listed.status_code == 200
    assert any(p["id"] == project_id for p in listed.json())

    assignments = await client.get(
        f"/api/v1/internal/organizations/{ORG_ID}/resource-assignments",
        headers=service,
    )
    assert assignments.status_code == 200
    assert isinstance(assignments.json(), list)
