"""Inventory internal API (snapshot cleanup)."""

from __future__ import annotations

import logging

import httpx

from huy_registry.config import Settings

logger = logging.getLogger(__name__)


async def delete_agent_snapshot(settings: Settings, agent_id: str) -> None:
    base = settings.inventory_url.rstrip("/")
    url = f"{base}/api/v1/internal/snapshots/{agent_id}"
    headers = {"X-Huy-Service-Token": settings.inventory_service_token}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(url, headers=headers)
            if response.status_code in (204, 404):
                return
            response.raise_for_status()
    except Exception:
        logger.warning("Failed to delete inventory snapshot for agent %s", agent_id, exc_info=True)
