"""Read infrastructure context from registry."""

from __future__ import annotations

from typing import Any

import httpx

from huy_compliance.config import Settings


class RegistryClient:
    def __init__(self, settings: Settings) -> None:
        self._base = settings.registry_url.rstrip("/")
        self._service_token = settings.projects_service_token

    def _service_headers(self) -> dict[str, str]:
        return {"X-Huy-Service-Token": self._service_token}

    async def list_provider_regions(self, provider_id: str) -> list[dict[str, Any]]:
        """Flat regions with parent_region_id (internal; no platform-admin JWT)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base}/api/v1/internal/infrastructure-providers/{provider_id}/regions",
                headers=self._service_headers(),
            )
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, list) else []

    async def get_agent(self, agent_id: str, bearer_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base}/api/v1/agents/{agent_id}",
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def get_provider(
        self, provider_id: str, bearer_token: str
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base}/api/v1/infrastructure-providers/{provider_id}",
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def get_region_tree_provider(
        self, provider_id: str, bearer_token: str
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base}/api/v1/infrastructure-providers/{provider_id}/region-tree",
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
            response.raise_for_status()
            return response.json()
