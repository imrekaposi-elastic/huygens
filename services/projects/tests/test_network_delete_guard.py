"""Network delete guards (VMs, links, breakout)."""

from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from helpers import ORG_ID, org_admin_token

from test_network_links import _mock_agent_connect


@pytest.mark.asyncio
@respx.mock
async def test_reject_delete_network_with_vms(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token(ORG_ID)}"}
    agent_id = "99999999-9999-9999-9999-999999999999"
    _mock_agent_connect(agent_id)
    respx.get("https://agent.test/api/v1/networks/lab0").mock(
        return_value=Response(200, json={"name": "lab0", "deletable": True})
    )
    respx.get("https://agent.test/api/v1/vms").mock(
        return_value=Response(
            200,
            json=[{"name": "web-01", "network": "lab0", "status": "on"}],
        )
    )

    project = await client.post(
        "/api/v1/projects",
        headers=headers,
        json={"organization_id": ORG_ID, "name": "VmNet", "slug": "vm-net"},
    )
    project_id = project.json()["id"]

    from huy_projects.db import get_session_factory
    from huy_projects.models import ProjectResource

    factory = get_session_factory()
    async with factory() as session:
        session.add(
            ProjectResource(
                project_id=project_id,
                agent_id=agent_id,
                resource_type="network",
                name="lab0",
                desired_state={"ipv4_cidr": "10.0.0.0/24"},
            )
        )
        await session.commit()

    denied = await client.delete(
        f"/api/v1/projects/{project_id}/agents/{agent_id}/networks/lab0",
        headers=headers,
    )
    assert denied.status_code == 409
    assert "VM" in denied.json()["detail"]
