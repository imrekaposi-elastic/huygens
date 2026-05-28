"""Qualitative characteristics and legacy trait migration (increment 6)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from helpers import ORG_ID, org_admin_token


@pytest.mark.asyncio
async def test_characteristic_crud_and_facets(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token()}"}
    base = f"/api/v1/organizations/{ORG_ID}"

    create = await client.post(
        f"{base}/qualitative-characteristics",
        headers=headers,
        json={
            "name": "EU Sovereign",
            "description": "Workloads must stay in EU",
            "moscow": "must",
            "kind": "placement",
        },
    )
    assert create.status_code == 201, create.text
    char_id = create.json()["id"]
    assert create.json()["slug"] == "eu-sovereign"

    patch = await client.patch(
        f"{base}/qualitative-characteristics/{char_id}",
        headers=headers,
        json={"moscow": "should"},
    )
    assert patch.status_code == 200
    assert patch.json()["moscow"] == "should"

    facets = await client.get(f"{base}/compliance-explorer/facets", headers=headers)
    assert facets.status_code == 200
    body = facets.json()
    assert "qualitative_characteristics" in body
    slugs = {c["slug"] for c in body["qualitative_characteristics"]}
    assert "eu-sovereign" in slugs
    assert "eu-sovereign" in body["trait_keys"]

    delete = await client.delete(
        f"{base}/qualitative-characteristics/{char_id}",
        headers=headers,
    )
    assert delete.status_code == 204


@pytest.mark.asyncio
async def test_legacy_trait_writes_deprecated(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token()}"}
    base = f"/api/v1/organizations/{ORG_ID}"
    provider_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    create = await client.post(
        f"{base}/infrastructure-providers/{provider_id}/traits",
        headers=headers,
        json={"trait_key": "legacy-eu", "title": "Legacy EU", "moscow": "must"},
    )
    assert create.status_code == 410

    listing = await client.get(
        f"{base}/infrastructure-providers/{provider_id}/traits",
        headers=headers,
    )
    assert listing.status_code == 200
    assert listing.headers.get("deprecation") == "true"


@pytest.mark.asyncio
async def test_migrate_legacy_traits(client: AsyncClient) -> None:
    from huy_compliance.db import get_session_factory
    from huy_compliance.schemas import TraitCreate
    from huy_compliance.services import catalog_service

    provider_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    region_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    factory = get_session_factory()
    async with factory() as session:
        await catalog_service.create_provider_trait(
            session,
            ORG_ID,
            provider_id,
            TraitCreate(trait_key="eu-legacy", title="EU Legacy", moscow="must"),
            actor_user_id="test",
        )
        await catalog_service.create_region_trait(
            session,
            ORG_ID,
            region_id,
            TraitCreate(trait_key="eu-legacy", title="EU Legacy Region", moscow="should"),
            actor_user_id="test",
        )
        await session.commit()

    headers = {"Authorization": f"Bearer {org_admin_token()}"}
    migrate = await client.post(
        f"/api/v1/organizations/{ORG_ID}/qualitative-characteristics/migrate-from-legacy-traits",
        headers=headers,
    )
    assert migrate.status_code == 200, migrate.text
    body = migrate.json()
    assert body["provider_traits_seen"] >= 1
    assert body["region_traits_seen"] >= 1
    assert body["provider_links_added"] >= 1
    assert body["region_links_added"] >= 1

    list_chars = await client.get(
        f"/api/v1/organizations/{ORG_ID}/qualitative-characteristics",
        headers=headers,
    )
    slugs = {c["slug"] for c in list_chars.json()}
    assert "eu-legacy" in slugs
