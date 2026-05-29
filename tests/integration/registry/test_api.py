"""Registry API against the running stack."""

from __future__ import annotations

import pytest

from http_client import ControlPlaneClient


@pytest.mark.integration
def test_protected_routes_require_bearer(cp: ControlPlaneClient) -> None:
    response = cp.get(f"{cp.stack.registry_url}/api/v1/agents", auth=False)
    assert response.status_code == 401


@pytest.mark.integration
def test_agent_technologies_list(cp: ControlPlaneClient) -> None:
    technologies = cp.registry("GET", "/api/v1/agent-technologies")
    assert technologies.status_code == 200, technologies.text
    assert any(t["slug"] == "libvirt-agent" for t in technologies.json())
