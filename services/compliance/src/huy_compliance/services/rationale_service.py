"""Placement explainability (know why)."""

from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from huy_compliance.config import Settings
from huy_compliance.models import ComplianceCheck, OrgComplianceItem
from huy_compliance.resource_keys import ResourceRef
from huy_compliance.schemas import PlacementRationaleOut, TraitSummary
from huy_compliance.services import catalog_service
from huy_compliance.services.placement_compliance import merge_catalog_items
from huy_compliance.services.placement_traits import inherited_placement_for_agent
from huy_compliance.services.registry_client import RegistryClient


async def build_placement_rationale(
    session: AsyncSession,
    settings: Settings,
    registry: RegistryClient,
    *,
    organization_id: str,
    ref: ResourceRef,
    bearer_token: str,
) -> PlacementRationaleOut:
    criticality = await catalog_service.get_asset_criticality(session, organization_id, ref)
    inherited: list[TraitSummary] = []
    inherited_items: list = []
    project_name: str | None = None
    agent_name: str | None = None
    region_id: str | None = None
    provider_id: str | None = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        project_r = await client.get(
            f"{settings.projects_url.rstrip('/')}/api/v1/projects/{ref.project_id}",
            headers={"Authorization": f"Bearer {bearer_token}"},
        )
        if project_r.status_code == 200:
            project_name = project_r.json().get("name")

    if ref.agent_id:
        inherited, inherited_items, agent = await inherited_placement_for_agent(
            session,
            registry,
            organization_id=organization_id,
            agent_id=ref.agent_id,
            bearer_token=bearer_token,
        )
        agent_name = agent.get("name")
        region_id = agent.get("region_id")
        provider_id = agent.get("infrastructure_provider_id")

    effective_items = merge_catalog_items(criticality.compliance_items, inherited_items)
    item_ids = [i.id for i in effective_items]
    related_checks: list = []
    if item_ids:
        result = await session.execute(
            select(ComplianceCheck, OrgComplianceItem.name)
            .join(OrgComplianceItem, OrgComplianceItem.id == ComplianceCheck.compliance_item_id)
            .where(
                ComplianceCheck.organization_id == organization_id,
                ComplianceCheck.compliance_item_id.in_(item_ids),
            )
        )
        related_checks = [
            catalog_service._check_out(check, name) for check, name in result.all()
        ]

    return PlacementRationaleOut(
        organization_id=organization_id,
        resource_type=ref.resource_type,  # type: ignore[arg-type]
        project_id=ref.project_id,
        agent_id=ref.agent_id,
        name=ref.name,
        project_name=project_name,
        agent_name=agent_name,
        region_id=region_id,
        infrastructure_provider_id=provider_id,
        inherited_traits=inherited,
        compliance_items=criticality.compliance_items,
        inherited_compliance_items=inherited_items,
        placement_note=criticality.placement_note,
        related_checks=related_checks,
        config_drift=None,
    )
