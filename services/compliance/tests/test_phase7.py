"""Phase 7 compliance API tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import respx
from httpx import AsyncClient, Response

from helpers import ORG_ID, compliance_engineer_token, org_admin_token


@pytest.mark.asyncio
async def test_catalog_crud(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token()}"}
    create = await client.post(
        f"/api/v1/organizations/{ORG_ID}/compliance-catalog",
        headers=headers,
        json={
            "name": "BIO Baseline",
            "slug": "bio-baseline",
            "description": "Baseline controls",
            "moscow": "must",
            "target_level": "high",
        },
    )
    assert create.status_code == 201, create.text
    item_id = create.json()["id"]

    listed = await client.get(
        f"/api/v1/organizations/{ORG_ID}/compliance-catalog",
        headers=headers,
    )
    assert listed.status_code == 200
    assert any(i["id"] == item_id for i in listed.json())

    patch = await client.patch(
        f"/api/v1/organizations/{ORG_ID}/compliance-catalog/{item_id}",
        headers=headers,
        json={"target_level": "critical"},
    )
    assert patch.status_code == 200
    assert patch.json()["target_level"] == "critical"

    delete = await client.delete(
        f"/api/v1/organizations/{ORG_ID}/compliance-catalog/{item_id}",
        headers=headers,
    )
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_asset_criticality_assignment(client: AsyncClient) -> None:
    admin = {"Authorization": f"Bearer {org_admin_token()}"}
    ce = {"Authorization": f"Bearer {compliance_engineer_token()}"}
    catalog = await client.post(
        f"/api/v1/organizations/{ORG_ID}/compliance-catalog",
        headers=admin,
        json={"name": "Tier 1", "slug": "tier-1", "moscow": "must"},
    )
    assert catalog.status_code == 201
    item_id = catalog.json()["id"]
    project_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

    put = await client.put(
        f"/api/v1/organizations/{ORG_ID}/projects/{project_id}/criticality",
        headers=ce,
        json={"compliance_item_ids": [item_id], "placement_note": "Pilot workload"},
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["placement_note"] == "Pilot workload"
    assert len(body["compliance_items"]) == 1


@pytest.mark.asyncio
@respx.mock
async def test_placement_rationale(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token()}"}
    provider_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    region_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    agent_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    project_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"

    respx.get(f"http://127.0.0.1:8084/api/v1/projects/{project_id}").mock(
        return_value=Response(200, json={"id": project_id, "name": "Lab"})
    )
    respx.get(f"http://127.0.0.1:8082/api/v1/agents/{agent_id}").mock(
        return_value=Response(
            200,
            json={
                "id": agent_id,
                "name": "dommel",
                "region_id": region_id,
                "infrastructure_provider_id": provider_id,
            },
        )
    )
    respx.get(f"http://127.0.0.1:8082/api/v1/infrastructure-providers/{provider_id}").mock(
        return_value=Response(200, json={"id": provider_id, "name": "On-prem"})
    )
    respx.get(
        f"http://127.0.0.1:8082/api/v1/infrastructure-providers/{provider_id}/region-tree"
    ).mock(
        return_value=Response(
            200,
            json=[{"id": region_id, "name": "Rack A", "children": [], "agents": []}],
        )
    )

    catalog_bio = await client.post(
        f"/api/v1/organizations/{ORG_ID}/compliance-catalog",
        headers=headers,
        json={"name": "EU residency", "slug": "eu-residency", "moscow": "must"},
    )
    eu_id = catalog_bio.json()["id"]
    catalog_bio2 = await client.post(
        f"/api/v1/organizations/{ORG_ID}/compliance-catalog",
        headers=headers,
        json={"name": "BIO hosting", "slug": "bio-hosting", "moscow": "should"},
    )
    bio_id = catalog_bio2.json()["id"]
    await client.put(
        f"/api/v1/organizations/{ORG_ID}/infrastructure-providers/{provider_id}/compliance-profile",
        headers=headers,
        json={"is_compliant": True, "compliance_item_ids": [eu_id]},
    )
    await client.put(
        f"/api/v1/organizations/{ORG_ID}/regions/{region_id}/compliance-items",
        headers=headers,
        json={"compliance_item_ids": [bio_id]},
    )

    rationale = await client.get(
        f"/api/v1/organizations/{ORG_ID}/resources/vm/placement-rationale",
        headers=headers,
        params={
            "project_id": project_id,
            "agent_id": agent_id,
            "name": "web-01",
        },
    )
    assert rationale.status_code == 200, rationale.text
    body = rationale.json()
    assert body["project_name"] == "Lab"
    assert len(body["inherited_traits"]) >= 2


@pytest.mark.asyncio
async def test_compliance_check_and_dashboard(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token()}"}
    catalog = await client.post(
        f"/api/v1/organizations/{ORG_ID}/compliance-catalog",
        headers=headers,
        json={"name": "ISO27001", "slug": "iso27001", "moscow": "should"},
    )
    item_id = catalog.json()["id"]
    valid_until = (datetime.now(UTC) + timedelta(days=90)).isoformat()
    check = await client.post(
        f"/api/v1/organizations/{ORG_ID}/compliance-checks",
        headers=headers,
        json={
            "compliance_item_id": item_id,
            "owner_user_id": "user-1",
            "owner_display": "Alice",
            "valid_until": valid_until,
        },
    )
    assert check.status_code == 201

    dash = await client.get(
        f"/api/v1/organizations/{ORG_ID}/compliance-dashboard",
        headers=headers,
    )
    assert dash.status_code == 200
    assert dash.json()["checks_active"] >= 1
