"""IPAM pool listing tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from helpers import ORG_ID, org_admin_token


@pytest.mark.asyncio
async def test_list_ipam_pools(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    created = await client.post(
        f"/api/v1/organizations/{ORG_ID}/ipam/pools",
        headers=headers,
        json={"name": "list-pool", "cidr": "10.90.0.0/24"},
    )
    assert created.status_code == 201, created.text
    pool_id = created.json()["id"]

    listed = await client.get(
        f"/api/v1/organizations/{ORG_ID}/ipam/pools",
        headers=headers,
    )
    assert listed.status_code == 200
    assert pool_id in {p["id"] for p in listed.json()}
