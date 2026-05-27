"""Network link API smoke tests (Phase 6)."""

from __future__ import annotations

import uuid

import pytest

pytestmark = pytest.mark.integration


def test_topology_and_overlay_pool_smoke(cp, ephemeral_org) -> None:
    org_id = str(ephemeral_org["id"])

    pool = cp.projects(
        "POST",
        f"/api/v1/organizations/{org_id}/ipam/pools",
        json={
            "name": f"overlay-{uuid.uuid4().hex[:6]}",
            "cidr": "10.253.0.0/24",
            "pool_kind": "overlay",
        },
    )
    assert pool.status_code == 201, pool.text
    assert pool.json()["pool_kind"] == "overlay"

    topo = cp.projects("GET", f"/api/v1/organizations/{org_id}/topology")
    assert topo.status_code == 200, topo.text
    body = topo.json()
    assert body["organization_id"] == org_id
    assert "vnets" in body and "links" in body

    links = cp.projects("GET", f"/api/v1/organizations/{org_id}/network-links")
    assert links.status_code == 200
    assert links.json() == []
