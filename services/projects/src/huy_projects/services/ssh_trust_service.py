"""SSH trust bootstrap: IAM org CA + libvirt agent cloud-init snippet."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from huy_ssh_onboard import build_guest_onboard_bundle as render_guest_onboard_bundle

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


async def resolve_linux_username(
    settings: Settings,
    *,
    organization_id: str,
    user_id: str,
    bearer_token: str,
    project_id: str | None = None,
) -> str | None:
    url = (
        f"{settings.iam_url.rstrip('/')}/api/v1/organizations/{organization_id}/ssh/account-mappings"
    )
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers={"Authorization": f"Bearer {bearer_token}"})
    if response.status_code >= 400:
        return None
    for row in response.json():
        if row.get("user_id") != user_id:
            continue
        mapped_project = row.get("project_id")
        if mapped_project and project_id and mapped_project != project_id:
            continue
        username = row.get("linux_username")
        if username:
            return str(username)
    return None


async def inject_ssh_trust_into_vm_create(
    settings: Settings,
    *,
    organization_id: str,
    project_id: str,
    user_id: str,
    bearer_token: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    """Merge org SSH CA into cloud-init for new VMs (no passwords; first boot only)."""
    if body.get("skip_ssh_trust"):
        body.pop("skip_ssh_trust", None)
        return body
    linux_username = body.pop("ssh_linux_username", None)
    if not linux_username:
        linux_username = await resolve_linux_username(
            settings,
            organization_id=organization_id,
            user_id=user_id,
            bearer_token=bearer_token,
            project_id=project_id,
        )
    if not linux_username:
        linux_username = settings.default_ssh_linux_username
    ca = await fetch_org_ssh_ca(
        settings, organization_id=organization_id, bearer_token=bearer_token
    )
    body["ssh_trust"] = {
        "ca_public_key_openssh": ca,
        "linux_username": linux_username,
        "sudoers_lines": [],
    }
    return body


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


async def get_vm_guest_onboard_bundle(
    settings: Settings,
    *,
    organization_id: str,
    project_id: str,
    project_name: str,
    user_id: str,
    bearer_token: str,
    vm_name: str,
    linux_username: str | None = None,
) -> dict[str, Any]:
    """Downloadable shell script for existing guests (any hypervisor)."""
    resolved = linux_username
    if not resolved:
        resolved = await resolve_linux_username(
            settings,
            organization_id=organization_id,
            user_id=user_id,
            bearer_token=bearer_token,
            project_id=project_id,
        )
    if not resolved:
        resolved = settings.default_ssh_linux_username
    ca = await fetch_org_ssh_ca(
        settings, organization_id=organization_id, bearer_token=bearer_token
    )
    return render_guest_onboard_bundle(
        ca_public_key_openssh=ca,
        linux_username=resolved,
        organization_id=organization_id,
        vm_name=vm_name,
        project_name=project_name,
    )
