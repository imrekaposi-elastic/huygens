"""Libvirt system networks (ADR 0007)."""

from __future__ import annotations

# Host infrastructure networks — not deletable via agent or console.
SYSTEM_READONLY_NETWORKS: frozenset[str] = frozenset({"default"})


def network_access_flags(name: str, *, agent_managed: bool) -> tuple[bool, bool]:
    """Return (readonly, deletable) for API responses."""
    if name in SYSTEM_READONLY_NETWORKS:
        return True, False
    if agent_managed:
        return False, True
    # Libvirt network without agent metadata: visible but not managed here.
    return True, False
