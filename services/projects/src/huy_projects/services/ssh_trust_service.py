"""SSH trust bootstrap: IAM org CA + libvirt agent cloud-init snippet."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from huy_projects.config import Settings
from huy_projects.services.agent_proxy import AgentProxy


async def fetch_org_ssh_ca(
    settings: Settings,
    *,
    organization_id: str,
    bearer_token: str,
) -> str:
    url = f"{settings.iam_url.rstrip('/')}/api/v1/organizations/{organization_id}/ssh/ca"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers={"Authorization": f"Bearer {bearer_token}"})
    if response.status_code == 404:
        raise HTTPException(
            status_code=502,
            detail="IAM SSH CA endpoint not found — rebuild iam service (Phase 9)",
        )
    if response.status_code >= 400:
        detail = response.text[:500] if response.text else response.reason_phrase
        raise HTTPException(status_code=response.status_code, detail=detail)
    data = response.json()
    return str(data["public_key_openssh"])


async def apply_vm_ssh_trust_setup(
    proxy: AgentProxy,
    settings: Settings,
    *,
    organization_id: str,
    agent_id: str,
    vm_name: str,
    linux_username: str,
    bearer_token: str,
    sudoers_lines: list[str] | None = None,
) -> dict[str, Any]:
    ca = await fetch_org_ssh_ca(
        settings, organization_id=organization_id, bearer_token=bearer_token
    )
    body = {
        "ca_public_key_openssh": ca,
        "linux_username": linux_username,
        "sudoers_lines": sudoers_lines or [],
    }
    try:
        return await proxy.apply_vm_ssh_trust(agent_id, organization_id, vm_name, body)
    except HTTPException as exc:
        if exc.status_code == 404:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Libvirt agent missing PUT /api/v1/vms/{name}/ssh-trust — "
                    "upgrade huy-libvirt-agent on the hypervisor (Phase 9)"
                ),
            ) from exc
        raise
