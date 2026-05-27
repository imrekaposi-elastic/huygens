"""Merge direct asset assignments with infrastructure-inherited catalog standards."""

from __future__ import annotations

from huy_compliance.schemas import ComplianceItemOut


def merge_catalog_items(*groups: list[ComplianceItemOut]) -> list[ComplianceItemOut]:
    """Return catalog items from multiple sources, deduplicated by id (first wins)."""
    seen: set[str] = set()
    merged: list[ComplianceItemOut] = []
    for group in groups:
        for item in group:
            if item.id in seen:
                continue
            seen.add(item.id)
            merged.append(item)
    return merged
