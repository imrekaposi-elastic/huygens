"""HTTP client for registry internal APIs."""

from __future__ import annotations

from datetime import datetime

import httpx

from huy_inventory.config import Settings


class RegistryClient:
    def __init__(self, settings: Settings) -> None:
        self._base = settings.registry_url.rstrip("/")
        self._token = settings.inventory_service_token

    def _headers(self) -> dict[str, str]:
        return {"X-Huy-Service-Token": self._token}

    async def fetch_poll_targets(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base}/api/v1/internal/poll-targets",
                headers=self._headers(),
            )
            response.raise_for_status()
            return response.json()

    async def report_poll_status(
        self,
        agent_id: str,
        *,
        connection_status: str,
        last_seen_at: datetime | None,
        last_poll_error: str | None,
    ) -> None:
        body = {
            "connection_status": connection_status,
            "last_seen_at": last_seen_at.isoformat() if last_seen_at else None,
            "last_poll_error": last_poll_error,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.patch(
                f"{self._base}/api/v1/internal/agents/{agent_id}/poll-status",
                headers=self._headers(),
                json=body,
            )
            response.raise_for_status()
