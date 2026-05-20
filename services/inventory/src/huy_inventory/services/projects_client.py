"""HTTP client for projects internal APIs."""

from __future__ import annotations

import httpx

from huy_inventory.config import Settings


class ProjectsClient:
    def __init__(self, settings: Settings) -> None:
        self._base = settings.projects_url.rstrip("/")
        self._token = settings.inventory_service_token

    def _headers(self) -> dict[str, str]:
        return {"X-Huy-Service-Token": self._token}

    async def fetch_resource_assignments(self, organization_id: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self._base}/api/v1/internal/organizations/{organization_id}/resource-assignments",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()


def assignments_by_resource(assignments: list[dict]) -> dict[tuple[str, str, str], dict]:
    """Key: (agent_id, resource_type, name)."""
    out: dict[tuple[str, str, str], dict] = {}
    for row in assignments:
        key = (row["agent_id"], row["resource_type"], row["name"])
        out[key] = row
    return out
