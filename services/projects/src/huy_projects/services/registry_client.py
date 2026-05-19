"""HTTP client for registry APIs."""

from __future__ import annotations

from typing import Any

import httpx

from huy_projects.config import Settings


class RegistryClient:
    def __init__(self, settings: Settings) -> None:
        self._base = settings.registry_url.rstrip("/")
        self._token = settings.projects_service_token

    def _service_headers(self) -> dict[str, str]:
        return {"X-Huy-Service-Token": self._token}

    async def fetch_agent_connect(self, agent_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base}/api/v1/internal/agents/{agent_id}/connect",
                headers=self._service_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def list_agents(self, bearer_token: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base}/api/v1/agents",
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
            response.raise_for_status()
            return response.json()
