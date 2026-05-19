"""Probe agent HTTPS endpoint for connection workflow."""

from __future__ import annotations

import httpx


async def probe_agent(
    base_url: str,
    agent_token: str,
    *,
    tls_verify: bool,
) -> tuple[bool, str | None]:
    url = f"{base_url.rstrip('/')}/api/v1/agent"
    headers = {"Authorization": f"Bearer {agent_token}"}
    try:
        async with httpx.AsyncClient(verify=tls_verify, timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return True, None
            return False, f"HTTP {response.status_code}: {response.text[:200]}"
    except Exception as exc:
        return False, str(exc)
