"""Same-hypervisor (local) link breakout payloads."""

from __future__ import annotations

from typing import Any

# Placeholder overlay_pool_id for links that do not consume overlay /30s.
LOCAL_LINK_POOL_ID = "00000000-0000-0000-0000-000000000001"


def disabled_wireguard() -> dict[str, Any]:
    return {
        "enabled": False,
        "interface": "wg-vnet",
        "listen_port": 51820,
        "private_key": "",
        "address": "",
        "peers": [],
        "vnet_routes": [],
        "nat_exempt_cidrs": [],
    }


def flat_local_peer(peer_vnet_cidr: str) -> dict[str, Any]:
    """Direct routing on one agent: iptables NAT exempt + forward between vnet CIDRs."""
    return {
        "enabled": True,
        "mode": "local_peer",
        "uplink": "",
        "remote_hypervisor_cidrs": [peer_vnet_cidr],
        "nat_exempt_cidrs": [peer_vnet_cidr],
    }


def disabled_flat() -> dict[str, Any]:
    return {
        "enabled": False,
        "mode": "bridge_uplink",
        "uplink": "",
        "remote_hypervisor_cidrs": [],
        "nat_exempt_cidrs": [],
    }
