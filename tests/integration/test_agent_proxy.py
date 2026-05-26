"""Projects service agent proxy against a real enrolled libvirt agent (optional)."""

from __future__ import annotations

import pytest

from http_client import ControlPlaneClient


def _connected_agents(cp: ControlPlaneClient, org_id: str) -> list[dict]:
    agents = cp.registry("GET", "/api/v1/agents").json()
    return [
        a
        for a in agents
        if a.get("organization_id") == org_id and a.get("connection_status") == "connected"
    ]


@pytest.mark.integration
@pytest.mark.requires_agent
def test_list_vms_via_projects_proxy(cp: ControlPlaneClient, target_org_id: str) -> None:
    agents = _connected_agents(cp, target_org_id)
    if not agents:
        pytest.skip("No connected agents for target org; enroll an agent or set HUY_E2E_ORG_ID")

    agent = agents[0]
    agent_id = str(agent["id"])

    projects = cp.projects("GET", f"/api/v1/projects?organization_id={target_org_id}").json()
    project_id: str | None = None
    for project in projects:
        listed = cp.projects(
            "GET",
            f"/api/v1/projects/{project['id']}/agents",
        )
        if listed.status_code == 200 and any(a["id"] == agent_id for a in listed.json()):
            project_id = str(project["id"])
            break

    if project_id is None:
        if not projects:
            created = cp.projects(
                "POST",
                "/api/v1/projects",
                json={
                    "organization_id": target_org_id,
                    "name": "E2E Agent Proxy",
                    "slug": "e2e-agent-proxy",
                },
            )
            assert created.status_code == 201, created.text
            project_id = str(created.json()["id"])
        else:
            project_id = str(projects[0]["id"])

        tech = cp.registry("GET", "/api/v1/agent-technologies").json()
        libvirt = next((t for t in tech if t["slug"] == "libvirt-agent"), None)
        assert libvirt is not None
        enabled = cp.projects(
            "PUT",
            f"/api/v1/projects/{project_id}/agent-technologies",
            json={"technologies": [{"agent_technology_id": libvirt["id"], "enabled": True}]},
        )
        assert enabled.status_code == 200, enabled.text

    vms = cp.projects(
        "GET",
        f"/api/v1/projects/{project_id}/agents/{agent_id}/vms",
    )
    assert vms.status_code == 200, vms.text
    assert isinstance(vms.json(), list)

    networks = cp.projects(
        "GET",
        f"/api/v1/projects/{project_id}/agents/{agent_id}/networks",
    )
    assert networks.status_code == 200, networks.text
    assert isinstance(networks.json(), list)
