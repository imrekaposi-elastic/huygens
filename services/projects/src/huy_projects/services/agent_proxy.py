"""Forward operator API calls to libvirt agents."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from huy_projects.services.registry_client import RegistryClient


class AgentProxy:
    def __init__(self, registry: RegistryClient) -> None:
        self._registry = registry

    async def _connect(self, agent_id: str, organization_id: str) -> dict[str, Any]:
        try:
            info = await self._registry.fetch_agent_connect(agent_id)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise HTTPException(status_code=404, detail="Agent not found") from exc
            raise HTTPException(status_code=502, detail="Registry unavailable") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Registry unavailable") from exc
        if info["organization_id"] != organization_id:
            raise HTTPException(status_code=403, detail="Agent not in project organization")
        return info

    def _client(self, info: dict[str, Any]) -> httpx.AsyncClient:
        headers = {"Authorization": f"Bearer {info['agent_token']}"}
        return httpx.AsyncClient(
            base_url=info["base_url"].rstrip("/"),
            headers=headers,
            timeout=120.0,
            verify=info.get("tls_verify", True),
        )

    async def _request(
        self,
        info: dict[str, Any],
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        async with self._client(info) as client:
            response = await client.request(method, path, json=json, params=params)
        if response.status_code >= 400:
            detail = response.text[:500] if response.text else response.reason_phrase
            raise HTTPException(status_code=response.status_code, detail=detail)
        return response

    async def list_vms(self, agent_id: str, organization_id: str) -> list[dict[str, Any]]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "GET", "/api/v1/vms")
        return response.json()

    async def get_vm(self, agent_id: str, organization_id: str, name: str) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "GET", f"/api/v1/vms/{name}")
        return response.json()

    async def create_vm(
        self, agent_id: str, organization_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "POST", "/api/v1/vms", json=body)
        return response.json()

    async def patch_vm(
        self, agent_id: str, organization_id: str, name: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "PATCH", f"/api/v1/vms/{name}", json=body)
        return response.json()

    async def delete_vm(self, agent_id: str, organization_id: str, name: str) -> None:
        info = await self._connect(agent_id, organization_id)
        await self._request(info, "DELETE", f"/api/v1/vms/{name}")

    async def get_agent(self, agent_id: str, organization_id: str) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "GET", "/api/v1/agent")
        return response.json()

    async def list_networks(self, agent_id: str, organization_id: str) -> list[dict[str, Any]]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "GET", "/api/v1/networks")
        return response.json()

    async def get_network(
        self, agent_id: str, organization_id: str, name: str
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "GET", f"/api/v1/networks/{name}")
        return response.json()

    async def create_network(
        self, agent_id: str, organization_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "POST", "/api/v1/networks", json=body)
        return response.json()

    async def patch_network(
        self, agent_id: str, organization_id: str, name: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "PATCH", f"/api/v1/networks/{name}", json=body)
        return response.json()

    async def list_cloud_init_profiles(
        self, agent_id: str, organization_id: str
    ) -> list[dict[str, Any]]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "GET", "/api/v1/cloud-init")
        return response.json()

    async def get_cloud_init_profile(
        self, agent_id: str, organization_id: str, name: str
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "GET", f"/api/v1/cloud-init/{name}")
        return response.json()

    async def create_cloud_init_profile(
        self, agent_id: str, organization_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "POST", "/api/v1/cloud-init", json=body)
        return response.json()

    async def update_cloud_init_profile(
        self, agent_id: str, organization_id: str, name: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(
            info, "PATCH", f"/api/v1/cloud-init/{name}", json=body
        )
        return response.json()

    async def delete_cloud_init_profile(
        self, agent_id: str, organization_id: str, name: str
    ) -> None:
        info = await self._connect(agent_id, organization_id)
        await self._request(info, "DELETE", f"/api/v1/cloud-init/{name}")

    async def validate_cloud_init(
        self, agent_id: str, organization_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(
            info, "POST", "/api/v1/cloud-init/validate", json=body
        )
        return response.json()

    async def list_images(self, agent_id: str, organization_id: str) -> list[dict[str, Any]]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "GET", "/api/v1/images")
        return response.json()

    async def get_image(
        self, agent_id: str, organization_id: str, name: str
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "GET", f"/api/v1/images/{name}")
        return response.json()

    async def create_image(
        self, agent_id: str, organization_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "POST", "/api/v1/images", json=body)
        return response.json()

    async def update_image(
        self, agent_id: str, organization_id: str, name: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "PATCH", f"/api/v1/images/{name}", json=body)
        return response.json()

    async def delete_image(self, agent_id: str, organization_id: str, name: str) -> None:
        info = await self._connect(agent_id, organization_id)
        await self._request(info, "DELETE", f"/api/v1/images/{name}")

    async def get_breakout(
        self, agent_id: str, organization_id: str, name: str
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(info, "GET", f"/api/v1/networks/{name}/breakout")
        return response.json()

    async def put_wireguard_breakout(
        self,
        agent_id: str,
        organization_id: str,
        name: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(
            info, "PUT", f"/api/v1/networks/{name}/breakout/wireguard", json=body
        )
        return response.json()

    async def put_flat_breakout(
        self,
        agent_id: str,
        organization_id: str,
        name: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        info = await self._connect(agent_id, organization_id)
        response = await self._request(
            info, "PUT", f"/api/v1/networks/{name}/breakout/flat", json=body
        )
        return response.json()

    async def delete_network(
        self,
        agent_id: str,
        organization_id: str,
        name: str,
        *,
        purge: bool = True,
    ) -> None:
        if name == "default":
            raise HTTPException(status_code=403, detail="Network 'default' is readonly")
        try:
            network = await self.get_network(agent_id, organization_id, name)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
            network = None
        if network is not None and (
            network.get("readonly") or not network.get("deletable", True)
        ):
            raise HTTPException(
                status_code=403,
                detail=f"Network '{name}' is readonly and cannot be deleted",
            )
        info = await self._connect(agent_id, organization_id)
        params = {"purge": "true"} if purge else None
        try:
            await self._request(info, "DELETE", f"/api/v1/networks/{name}", params=params)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
