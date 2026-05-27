"""Compliance explorer filter tests."""

from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from helpers import ORG_ID, org_admin_token


def _region_json(
    region_id: str,
    provider_id: str,
    *,
    name: str,
    slug: str,
    parent_region_id: str | None = None,
) -> dict:
    return {
        "id": region_id,
        "infrastructure_provider_id": provider_id,
        "parent_region_id": parent_region_id,
        "name": name,
        "slug": slug,
        "created_at": "2024-01-01T00:00:00+00:00",
    }


def _mock_provider_regions(respx_module, provider_id: str, regions: list[dict]) -> None:
    respx_module.get(
        f"http://127.0.0.1:8082/api/v1/internal/infrastructure-providers/{provider_id}/regions"
    ).mock(return_value=Response(200, json=regions))


@pytest.mark.asyncio
@respx.mock
async def test_explorer_missing_catalog_and_trait_filter(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token()}"}
    agent_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    project_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    provider_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    region_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"

    respx.get(
        f"http://127.0.0.1:8084/api/v1/internal/organizations/{ORG_ID}/resource-assignments"
    ).mock(
        return_value=Response(
            200,
            json=[
                {
                    "agent_id": agent_id,
                    "resource_type": "vm",
                    "name": "web-01",
                    "project_id": project_id,
                    "project_name": "Lab",
                    "project_slug": "lab",
                }
            ],
        )
    )
    respx.get(
        f"http://127.0.0.1:8084/api/v1/internal/organizations/{ORG_ID}/projects"
    ).mock(
        return_value=Response(
            200,
            json=[
                {
                    "id": project_id,
                    "organization_id": ORG_ID,
                    "name": "Lab",
                    "slug": "lab",
                }
            ],
        )
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
    # Registry infrastructure routes are platform-admin only; compliance must not depend on them.
    respx.get(f"http://127.0.0.1:8082/api/v1/infrastructure-providers/{provider_id}").mock(
        return_value=Response(403, json={"detail": "platform_admin required"})
    )
    respx.get(
        f"http://127.0.0.1:8082/api/v1/infrastructure-providers/{provider_id}/region-tree"
    ).mock(
        return_value=Response(403, json={"detail": "platform_admin required"})
    )
    _mock_provider_regions(
        respx,
        provider_id,
        [_region_json(region_id, provider_id, name="EU West", slug="eu-west")],
    )

    bio_catalog = await client.post(
        f"/api/v1/organizations/{ORG_ID}/compliance-catalog",
        headers=headers,
        json={"name": "BIO Baseline", "slug": "bio-baseline", "moscow": "must"},
    )
    bio_id = bio_catalog.json()["id"]
    eu_catalog = await client.post(
        f"/api/v1/organizations/{ORG_ID}/compliance-catalog",
        headers=headers,
        json={"name": "EU residency", "slug": "eu-residency", "moscow": "must"},
    )
    eu_id = eu_catalog.json()["id"]
    provider_eu = await client.put(
        f"/api/v1/organizations/{ORG_ID}/infrastructure-providers/{provider_id}/compliance-profile",
        headers=headers,
        json={"compliance_item_ids": [eu_id]},
    )
    assert provider_eu.status_code == 200

    missing_eu = await client.get(
        f"/api/v1/organizations/{ORG_ID}/compliance-explorer",
        headers=headers,
        params={"catalog_slug": "eu-residency", "catalog_match": "missing"},
    )
    assert missing_eu.status_code == 200
    assert missing_eu.json()["total_matched"] == 0
    # Provider-linked EU should appear as inherited on the VM row when listed.
    has_eu = await client.get(
        f"/api/v1/organizations/{ORG_ID}/compliance-explorer",
        headers=headers,
        params={"catalog_slug": "eu-residency", "catalog_match": "has"},
    )
    assert has_eu.status_code == 200
    assert has_eu.json()["total_matched"] >= 1
    vm_row = next((r for r in has_eu.json()["rows"] if r.get("name") == "web-01"), None)
    assert vm_row is not None
    inherited_ids = {i["id"] for i in vm_row.get("inherited_catalog_items") or []}
    assert eu_id in inherited_ids or eu_id in {i["id"] for i in vm_row.get("catalog_items") or []}

    await client.put(
        f"/api/v1/organizations/{ORG_ID}/regions/{region_id}/compliance-items",
        headers=headers,
        json={"compliance_item_ids": [eu_id]},
    )

    missing_bio = await client.get(
        f"/api/v1/organizations/{ORG_ID}/compliance-explorer",
        headers=headers,
        params={
            "catalog_slug": "bio-baseline",
            "catalog_match": "missing",
            "resource_type": "vm",
        },
    )
    assert missing_bio.status_code == 200
    body = missing_bio.json()
    assert body["total_matched"] == 1
    assert body["rows"][0]["name"] == "web-01"
    assert body["page_size"] == 25
    assert body["offset"] == 0

    suggest = await client.get(
        f"/api/v1/organizations/{ORG_ID}/compliance-explorer/suggest",
        headers=headers,
        params={"q": "web"},
    )
    assert suggest.status_code == 200
    assert any(s["name"] == "web-01" for s in suggest.json()["suggestions"])

    in_eu = await client.get(
        f"/api/v1/organizations/{ORG_ID}/compliance-explorer",
        headers=headers,
        params={"trait_key": "eu", "trait_match": "has"},
    )
    assert in_eu.status_code == 200
    assert in_eu.json()["total_matched"] == 1

    await client.put(
        f"/api/v1/organizations/{ORG_ID}/projects/{project_id}/resources/vm/web-01/criticality",
        headers=headers,
        params={"agent_id": agent_id},
        json={"compliance_item_ids": [bio_id]},
    )
    missing_after = await client.get(
        f"/api/v1/organizations/{ORG_ID}/compliance-explorer",
        headers=headers,
        params={
            "catalog_slug": "bio-baseline",
            "catalog_match": "missing",
            "resource_type": "vm",
        },
    )
    assert missing_after.json()["total_matched"] == 0


@pytest.mark.asyncio
@respx.mock
async def test_inherits_parent_region_compliance(client: AsyncClient) -> None:
    """Standards on Falkenstein (parent) must reach agents placed in FS6 (child)."""
    headers = {"Authorization": f"Bearer {org_admin_token()}"}
    agent_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    project_id = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    provider_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    parent_region_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    child_region_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"

    respx.get(
        f"http://127.0.0.1:8084/api/v1/internal/organizations/{ORG_ID}/resource-assignments"
    ).mock(
        return_value=Response(
            200,
            json=[
                {
                    "agent_id": agent_id,
                    "resource_type": "vm",
                    "name": "fs6-vm",
                    "project_id": project_id,
                }
            ],
        )
    )
    respx.get(
        f"http://127.0.0.1:8084/api/v1/internal/organizations/{ORG_ID}/projects"
    ).mock(return_value=Response(200, json=[]))
    respx.get(f"http://127.0.0.1:8082/api/v1/agents/{agent_id}").mock(
        return_value=Response(
            200,
            json={
                "id": agent_id,
                "name": "hetzner-agent",
                "region_id": child_region_id,
                "infrastructure_provider_id": provider_id,
            },
        )
    )
    _mock_provider_regions(
        respx,
        provider_id,
        [
            _region_json(
                parent_region_id,
                provider_id,
                name="Falkenstein",
                slug="falkenstein",
            ),
            _region_json(
                child_region_id,
                provider_id,
                name="FS6",
                slug="fs6",
                parent_region_id=parent_region_id,
            ),
        ],
    )

    bio = await client.post(
        f"/api/v1/organizations/{ORG_ID}/compliance-catalog",
        headers=headers,
        json={"name": "BIO Baseline", "slug": "bio-baseline", "moscow": "must"},
    )
    bio_id = bio.json()["id"]

    # Standards only on parent Falkenstein — not on FS6 child.
    await client.put(
        f"/api/v1/organizations/{ORG_ID}/regions/{parent_region_id}/compliance-items",
        headers=headers,
        json={"compliance_item_ids": [bio_id]},
    )

    has_bio = await client.get(
        f"/api/v1/organizations/{ORG_ID}/compliance-explorer",
        headers=headers,
        params={"catalog_slug": "bio-baseline", "catalog_match": "has"},
    )
    assert has_bio.status_code == 200
    assert has_bio.json()["total_matched"] >= 1
    row = has_bio.json()["rows"][0]
    inherited_ids = {i["id"] for i in row.get("inherited_catalog_items") or []}
    assert bio_id in inherited_ids
