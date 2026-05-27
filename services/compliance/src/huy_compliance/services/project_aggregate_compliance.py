"""Project compliance derived from all child VMs and networks."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from huy_compliance.resource_keys import ResourceRef
from huy_compliance.schemas import ComplianceItemOut
from huy_compliance.services import catalog_service
from huy_compliance.services.placement_compliance import merge_catalog_items
from huy_compliance.services.placement_traits import inherited_placement_for_agent
from huy_compliance.services.registry_client import RegistryClient

_CHILD_TYPES = frozenset({"vm", "network"})


async def effective_items_for_assignment(
    session: AsyncSession,
    registry: RegistryClient,
    *,
    organization_id: str,
    assignment: dict[str, Any],
    criticality_map: dict[str, tuple[list[ComplianceItemOut], str | None]],
    bearer_token: str,
    agent_cache: dict[str, dict[str, Any]],
    region_parent_cache: dict[str, dict[str, str | None]],
    region_name_cache: dict[str, dict[str, str]],
) -> list[ComplianceItemOut]:
    """Direct + placement-inherited catalog standards for one VM or network."""
    rtype = assignment["resource_type"]
    if rtype not in _CHILD_TYPES:
        return []
    project_id = assignment["project_id"]
    agent_id = assignment.get("agent_id")
    name = assignment.get("name")
    if not agent_id:
        return []
    ref = ResourceRef.from_parts(
        rtype, project_id=project_id, agent_id=agent_id, name=name
    )
    direct_items, _ = criticality_map.get(ref.key(), ([], None))
    _, placement_inherited, _ = await inherited_placement_for_agent(
        session,
        registry,
        organization_id=organization_id,
        agent_id=agent_id,
        bearer_token=bearer_token,
        agent_cache=agent_cache,
        region_parent_cache=region_parent_cache,
        region_name_cache=region_name_cache,
    )
    return merge_catalog_items(direct_items, placement_inherited)


async def aggregate_items_for_project(
    session: AsyncSession,
    registry: RegistryClient,
    *,
    organization_id: str,
    project_id: str,
    assignments: list[dict[str, Any]],
    criticality_map: dict[str, tuple[list[ComplianceItemOut], str | None]],
    bearer_token: str,
    agent_cache: dict[str, dict[str, Any]] | None = None,
    region_parent_cache: dict[str, dict[str, str | None]] | None = None,
    region_name_cache: dict[str, dict[str, str]] | None = None,
) -> list[ComplianceItemOut]:
    """Catalog items every VM and network in the project satisfies (effective compliance)."""
    agent_cache = agent_cache if agent_cache is not None else {}
    region_parent_cache = (
        region_parent_cache if region_parent_cache is not None else {}
    )
    region_name_cache = region_name_cache if region_name_cache is not None else {}

    children = [
        a
        for a in assignments
        if a.get("project_id") == project_id
        and a.get("resource_type") in _CHILD_TYPES
        and a.get("agent_id")
    ]
    if not children:
        return []

    per_child_ids: list[set[str]] = []
    item_by_id: dict[str, ComplianceItemOut] = {}

    for child in children:
        effective = await effective_items_for_assignment(
            session,
            registry,
            organization_id=organization_id,
            assignment=child,
            criticality_map=criticality_map,
            bearer_token=bearer_token,
            agent_cache=agent_cache,
            region_parent_cache=region_parent_cache,
            region_name_cache=region_name_cache,
        )
        per_child_ids.append({item.id for item in effective})
        for item in effective:
            item_by_id[item.id] = item

    common_ids = set.intersection(*per_child_ids)
    return [item_by_id[i] for i in sorted(common_ids, key=lambda cid: item_by_id[cid].name)]
