"""Projects internal API (resource assignments)."""

from __future__ import annotations

from typing import Any

import httpx

from huy_compliance.config import Settings


class ProjectsClient:
    def __init__(self, settings: Settings) -> None:
        self._base = settings.projects_url.rstrip("/")
        self._token = settings.projects_service_token

    def _headers(self) -> dict[str, str]:
        return {"X-Huy-Service-Token": self._token}

    async def list_resource_assignments(self, organization_id: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base}/api/v1/internal/organizations/{organization_id}/resource-assignments",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def list_organization_projects(self, organization_id: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base}/api/v1/internal/organizations/{organization_id}/projects",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()
