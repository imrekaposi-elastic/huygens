"""JWT issued by IAM must authorize registry, inventory, and projects."""

from __future__ import annotations

import pytest

from http_client import ControlPlaneClient


@pytest.mark.integration
def test_login_rejects_invalid_credentials(cp: ControlPlaneClient) -> None:
    response = cp.web(
        "POST",
        "/api/v1/auth/login",
        auth=False,
        json={"username": cp.stack.username, "password": "wrong-password"},
    )
    assert response.status_code == 401


@pytest.mark.integration
def test_me_returns_platform_admin(cp: ControlPlaneClient) -> None:
    response = cp.iam("GET", "/api/v1/auth/me")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["username"] == cp.stack.username
    assert "platform_admin" in body.get("platform_roles", [])


@pytest.mark.integration
def test_protected_routes_require_bearer(cp: ControlPlaneClient) -> None:
    for base, path in (
        (cp.stack.registry_url, "/api/v1/agents"),
        (cp.stack.inventory_url, "/api/v1/inventory/agents"),
        (cp.stack.projects_url, "/api/v1/projects"),
    ):
        response = cp.get(f"{base}{path}", auth=False)
        assert response.status_code == 401, f"expected 401 for unauthenticated GET {path}"


@pytest.mark.integration
def test_jwt_works_on_registry_inventory_and_projects(cp: ControlPlaneClient, target_org_id: str) -> None:
    technologies = cp.registry("GET", "/api/v1/agent-technologies")
    assert technologies.status_code == 200, technologies.text
    assert any(t["slug"] == "libvirt-agent" for t in technologies.json())

    agents = cp.inventory("GET", "/api/v1/inventory/agents")
    assert agents.status_code == 200, agents.text

    dashboard = cp.inventory(
        "GET",
        f"/api/v1/inventory/organizations/{target_org_id}/dashboard",
    )
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["organization_id"] == target_org_id

    projects = cp.projects("GET", f"/api/v1/projects?organization_id={target_org_id}")
    assert projects.status_code == 200, projects.text
