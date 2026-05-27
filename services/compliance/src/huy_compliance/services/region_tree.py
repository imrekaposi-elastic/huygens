"""Helpers for registry region trees."""

from __future__ import annotations

from typing import Any


def parent_map_from_regions(regions: list[dict[str, Any]]) -> dict[str, str | None]:
    """Build region_id → parent_region_id from flat registry region rows."""
    return {r["id"]: r.get("parent_region_id") for r in regions}


def ancestor_region_ids(
    region_id: str, parent_by_id: dict[str, str | None]
) -> list[str]:
    """Nearest placement region first, then each ancestor up to the provider root."""
    out: list[str] = []
    current: str | None = region_id
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        out.append(current)
        current = parent_by_id.get(current)
    return out


def find_region_name(nodes: list[dict[str, Any]] | dict[str, Any], region_id: str) -> str | None:
    if isinstance(nodes, dict):
        nodes = nodes.get("region_tree") or [nodes]
    for node in nodes:
        if node.get("id") == region_id:
            return node.get("name")
        children = node.get("children") or []
        found = find_region_name(children, region_id)
        if found:
            return found
    return None
