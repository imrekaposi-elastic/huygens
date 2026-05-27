"""Project aggregate compliance (all children must satisfy a standard)."""

from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from helpers import ORG_ID, org_admin_token
from respx_helpers import mock_org_projects, mock_resource_assignments
from test_explorer import _mock_provider_regions, _region_json


@pytest.mark.asyncio
@respx.mock
async def test_project_inherits_when_all_children_compliant(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token()}"}
    agent_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    agent_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    project_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    provider_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    region_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"

    mock_resource_assignments(
        respx,
        [
            {
                "agent_id": agent_a,
                "resource_type": "vm",
                "name": "vm-a",
                "project_id": project_id,
            },
            {
                "agent_id": agent_b,
                "resource_type": "network",
                "name": "net-b",
                "project_id": project_id,
            },
        ],
    )
    mock_org_projects(
        respx,
        projects=[
            {
                "id": project_id,
                "organization_id": ORG_ID,
                "name": "Aggregate Lab",
                "slug": "agg-lab",
            }
        ],
    )
    for agent_id in (agent_a, agent_b):
        respx.get(f"http://127.0.0.1:8082/api/v1/agents/{agent_id}").mock(
            return_value=Response(
                200,
                json={
                    "id": agent_id,
                    "name": agent_id[:8],
                    "region_id": region_id,
                    "infrastructure_provider_id": provider_id,
                },
            )
        )
    _mock_provider_regions(
        respx,
        provider_id,
        [_region_json(region_id, provider_id, name="EU", slug="eu")],
    )

    eu = await client.post(
        f"/api/v1/organizations/{ORG_ID}/compliance-catalog",
        headers=headers,
        json={"name": "Data EU", "slug": "data-eu", "moscow": "must"},
    )
    eu_id = eu.json()["id"]

    await client.put(
        f"/api/v1/organizations/{ORG_ID}/projects/{project_id}/resources/vm/vm-a/criticality",
        headers=headers,
        params={"agent_id": agent_a},
        json={"compliance_item_ids": [eu_id]},
    )
    await client.put(
        f"/api/v1/organizations/{ORG_ID}/projects/{project_id}/resources/network/net-b/criticality",
        headers=headers,
        params={"agent_id": agent_b},
        json={"compliance_item_ids": [eu_id]},
    )

    project = await client.get(
        f"/api/v1/organizations/{ORG_ID}/projects/{project_id}/criticality",
        headers=headers,
    )
    assert project.status_code == 200
    agg_ids = {i["id"] for i in project.json().get("aggregate_compliance_items") or []}
    assert eu_id in agg_ids

    explorer = await client.get(
        f"/api/v1/organizations/{ORG_ID}/compliance-explorer",
        headers=headers,
        params={"resource_type": "project", "catalog_slug": "data-eu", "catalog_match": "has"},
    )
    assert explorer.status_code == 200
    assert explorer.json()["total_matched"] >= 1
    row = next(
        (r for r in explorer.json()["rows"] if r["project_id"] == project_id),
        None,
    )
    assert row is not None
    assert eu_id in {i["id"] for i in row.get("aggregate_catalog_items") or []}


@pytest.mark.asyncio
@respx.mock
async def test_project_no_aggregate_when_one_child_missing(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token()}"}
    agent_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    agent_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    project_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    provider_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    region_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"

    mock_resource_assignments(
        respx,
        [
            {
                "agent_id": agent_a,
                "resource_type": "vm",
                "name": "vm-a",
                "project_id": project_id,
            },
            {
                "agent_id": agent_b,
                "resource_type": "vm",
                "name": "vm-b",
                "project_id": project_id,
            },
        ],
    )
    mock_org_projects(respx)
    for agent_id in (agent_a, agent_b):
        respx.get(f"http://127.0.0.1:8082/api/v1/agents/{agent_id}").mock(
            return_value=Response(
                200,
                json={
                    "id": agent_id,
                    "region_id": region_id,
                    "infrastructure_provider_id": provider_id,
                },
            )
        )
    _mock_provider_regions(
        respx,
        provider_id,
        [_region_json(region_id, provider_id, name="EU", slug="eu")],
    )

    eu = await client.post(
        f"/api/v1/organizations/{ORG_ID}/compliance-catalog",
        headers=headers,
        json={"name": "Data EU", "slug": "data-eu", "moscow": "must"},
    )
    eu_id = eu.json()["id"]

    await client.put(
        f"/api/v1/organizations/{ORG_ID}/projects/{project_id}/resources/vm/vm-a/criticality",
        headers=headers,
        params={"agent_id": agent_a},
        json={"compliance_item_ids": [eu_id]},
    )
    await client.put(
        f"/api/v1/organizations/{ORG_ID}/projects/{project_id}/resources/vm/vm-b/criticality",
        headers=headers,
        params={"agent_id": agent_b},
        json={"compliance_item_ids": []},
    )

    project = await client.get(
        f"/api/v1/organizations/{ORG_ID}/projects/{project_id}/criticality",
        headers=headers,
    )
    assert project.status_code == 200
    assert not project.json().get("aggregate_compliance_items")
