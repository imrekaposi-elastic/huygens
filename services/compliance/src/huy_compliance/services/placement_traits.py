"""Resolve inherited provider/region compliance catalog items for an agent."""

from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from huy_compliance.schemas import ComplianceItemOut, TraitSummary
from huy_compliance.services import infrastructure_compliance_service
from huy_compliance.services.registry_client import RegistryClient
from huy_compliance.services.region_tree import (
    ancestor_region_ids,
    parent_map_from_regions,
)


async def inherited_placement_for_agent(
    session: AsyncSession,
    registry: RegistryClient,
    *,
    organization_id: str,
    agent_id: str,
    bearer_token: str,
    agent_cache: dict[str, dict[str, Any]] | None = None,
    region_parent_cache: dict[str, dict[str, str | None]] | None = None,
    region_name_cache: dict[str, dict[str, str]] | None = None,
) -> tuple[list[TraitSummary], list[ComplianceItemOut], dict[str, Any]]:
    """Return placement traits, inherited catalog items, and agent JSON."""
    agent_cache = agent_cache if agent_cache is not None else {}
    region_parent_cache = (
        region_parent_cache if region_parent_cache is not None else {}
    )
    region_name_cache = region_name_cache if region_name_cache is not None else {}

    if agent_id in agent_cache:
        agent = agent_cache[agent_id]
    else:
        agent = await registry.get_agent(agent_id, bearer_token)
        agent_cache[agent_id] = agent

    inherited_traits: list[TraitSummary] = []
    inherited_items: list[ComplianceItemOut] = []
    region_id = agent.get("region_id")
    provider_id = agent.get("infrastructure_provider_id")
    if provider_id:
        # Provider catalog links live in compliance DB; registry provider GET is platform-admin only.
        profile = await infrastructure_compliance_service.get_provider_compliance(
            session, organization_id, provider_id
        )
        for item in profile.compliance_items:
            inherited_items.append(item)
            inherited_traits.append(
                TraitSummary(
                    scope="provider",
                    trait_key=item.slug,
                    title=item.name,
                    description=item.description,
                    moscow=item.moscow,
                    infrastructure_provider_id=provider_id,
                )
            )

    if region_id and provider_id:
        if provider_id not in region_parent_cache:
            try:
                flat_regions = await registry.list_provider_regions(provider_id)
            except httpx.HTTPError:
                flat_regions = []
            region_parent_cache[provider_id] = parent_map_from_regions(flat_regions)
            region_name_cache[provider_id] = {
                r["id"]: r.get("name") or r["id"] for r in flat_regions
            }
        parent_by_id = region_parent_cache[provider_id]
        names_by_id = region_name_cache.get(provider_id, {})
        lineage = ancestor_region_ids(region_id, parent_by_id)
        for source_region_id, item in (
            await infrastructure_compliance_service.catalog_items_for_region_lineage(
                session, organization_id, lineage
            )
        ):
            if any(existing.id == item.id for existing in inherited_items):
                continue
            inherited_items.append(item)
            inherited_traits.append(
                TraitSummary(
                    scope="region",
                    trait_key=item.slug,
                    title=item.name,
                    description=item.description,
                    moscow=item.moscow,
                    region_id=source_region_id,
                    region_name=names_by_id.get(source_region_id),
                )
            )

    return inherited_traits, inherited_items, agent


async def inherited_traits_for_agent(
    session: AsyncSession,
    registry: RegistryClient,
    *,
    organization_id: str,
    agent_id: str,
    bearer_token: str,
    agent_cache: dict[str, dict[str, Any]] | None = None,
    region_parent_cache: dict[str, dict[str, str | None]] | None = None,
    region_name_cache: dict[str, dict[str, str]] | None = None,
) -> tuple[list[TraitSummary], dict[str, Any]]:
    """Return trait summaries and agent JSON (region_id, provider_id, name)."""
    traits, _, agent = await inherited_placement_for_agent(
        session,
        registry,
        organization_id=organization_id,
        agent_id=agent_id,
        bearer_token=bearer_token,
        agent_cache=agent_cache,
        region_parent_cache=region_parent_cache,
        region_name_cache=region_name_cache,
    )
    return traits, agent
