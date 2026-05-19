"""Poll libvirt agent read-path APIs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import structlog

logger = structlog.get_logger(__name__)


def _normalize_vm(vm: dict) -> dict:
    return {
        "name": vm.get("name"),
        "uuid": vm.get("uuid"),
        "state": vm.get("libvirt_state") or vm.get("status"),
        "ips": [vm["guest_ip"]] if vm.get("guest_ip") else [],
        "networks": [vm["network"]] if vm.get("network") else [],
    }


def _normalize_network(net: dict) -> dict:
    return {
        "name": net.get("name"),
        "active": net.get("active"),
        "readonly": net.get("readonly"),
        "bridge": net.get("bridge"),
    }


async def poll_agent(target: dict) -> tuple[dict[str, Any] | None, str | None]:
    base = target["base_url"].rstrip("/")
    token = target["agent_token"]
    headers = {"Authorization": f"Bearer {token}"}
    verify = target.get("tls_verify", True)
    try:
        async with httpx.AsyncClient(verify=verify, timeout=30.0) as client:
            agent_r = await client.get(f"{base}/api/v1/agent", headers=headers)
            vms_r = await client.get(f"{base}/api/v1/vms", headers=headers)
            nets_r = await client.get(f"{base}/api/v1/networks", headers=headers)
            for response in (agent_r, vms_r, nets_r):
                if response.status_code != 200:
                    return None, f"{response.request.url}: HTTP {response.status_code}"
            vms_raw = vms_r.json()
            nets_raw = nets_r.json()
            payload = {
                "version": 1,
                "agent_id": target["agent_id"],
                "organization_id": target["organization_id"],
                "region_id": target["region_id"],
                "polled_at": datetime.now(UTC).isoformat(),
                "agent": agent_r.json(),
                "vms": [_normalize_vm(v) for v in vms_raw],
                "networks": [_normalize_network(n) for n in nets_raw],
                "config_drift": False,
            }
            return payload, None
    except Exception as exc:
        logger.warning("agent_poll_failed", agent_id=target.get("agent_id"), error=str(exc))
        return None, str(exc)
