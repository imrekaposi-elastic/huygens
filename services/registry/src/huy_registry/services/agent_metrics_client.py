"""Fetch JSON metrics snapshot from a libvirt agent."""

from __future__ import annotations

import httpx
from fastapi import HTTPException


async def fetch_agent_metrics(
    base_url: str,
    agent_token: str,
    *,
    tls_verify: bool,
) -> dict:
    url = f"{base_url.rstrip('/')}/api/v1/agent/metrics"
    headers = {"Authorization": f"Bearer {agent_token}"}
    try:
        async with httpx.AsyncClient(verify=tls_verify, timeout=15.0) as client:
            response = await client.get(url, headers=headers)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent unreachable: {exc}") from exc
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Agent metrics HTTP {response.status_code}: {response.text[:300]}",
        )
    return response.json()
