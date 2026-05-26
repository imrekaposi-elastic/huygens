"""End-to-end operator path: org → project → IPAM wizard (no libvirt agent required)."""

from __future__ import annotations

import pytest

from http_client import ControlPlaneClient


@pytest.mark.integration
def test_ephemeral_org_project_and_ipam_wizard(
    cp: ControlPlaneClient,
    ephemeral_org: dict,
    ephemeral_project: dict,
) -> None:
    org_id = str(ephemeral_org["id"])
    project_id = str(ephemeral_project["id"])

    pool = cp.projects(
        "POST",
        f"/api/v1/organizations/{org_id}/ipam/pools",
        json={
            "name": "e2e-pool",
            "cidr": "10.200.0.0/20",
            "exceptions": ["10.200.0.0/28"],
            "description": "integration test pool",
        },
    )
    assert pool.status_code == 201, pool.text
    pool_id = pool.json()["id"]

    listed = cp.projects("GET", f"/api/v1/organizations/{org_id}/ipam/pools")
    assert listed.status_code == 200
    assert any(p["id"] == pool_id for p in listed.json())

    plan = cp.projects(
        "POST",
        f"/api/v1/organizations/{org_id}/ipam/wizard/plan",
        json={"pool_id": pool_id, "network_count": 2, "hosts_per_network": 16},
    )
    assert plan.status_code == 200, plan.text
    subnets = plan.json()["subnets"]
    assert len(subnets) == 2
    assert all("cidr" in row for row in subnets)

    # Project remains readable through projects API (JWT + org scope).
    fetched = cp.projects("GET", f"/api/v1/projects/{project_id}")
    assert fetched.status_code == 200
    assert fetched.json()["slug"] == ephemeral_project["slug"]
