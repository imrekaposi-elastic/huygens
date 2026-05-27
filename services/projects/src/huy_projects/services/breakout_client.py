"""HTTP client for the breakout-controller (WireGuard link planning)."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from huy_projects.config import Settings


class BreakoutControllerClient:
    def __init__(self, settings: Settings) -> None:
        self._base = settings.breakout_controller_url.rstrip("/")
        self._token = settings.breakout_service_token

    def _headers(self) -> dict[str, str]:
        return {"X-Huy-Service-Token": self._token}

    async def plan_link(self, body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self._base}/v1/links/plan",
                    json=body,
                    headers=self._headers(),
                )
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=502, detail="Breakout controller unavailable"
                ) from exc
        if response.status_code >= 400:
            detail = response.text[:500] if response.text else response.reason_phrase
            raise HTTPException(status_code=502, detail=f"Breakout plan failed: {detail}")
        return response.json()

    async def revoke_link(self, body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self._base}/v1/links/revoke",
                    json=body,
                    headers=self._headers(),
                )
            except httpx.HTTPError as exc:
                raise HTTPException(
                    status_code=502, detail="Breakout controller unavailable"
                ) from exc
        if response.status_code >= 400:
            detail = response.text[:500] if response.text else response.reason_phrase
            raise HTTPException(status_code=502, detail=f"Breakout revoke failed: {detail}")
        return response.json()
