"""Compliance explorer — filter workloads by catalog assignment and placement traits."""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from huy_compliance.config import Settings
from huy_compliance.models import (
    AssetCriticalityAssignment,
    InfrastructureProviderCompliance,
    InfrastructureProviderComplianceItemLink,
    OrgComplianceItem,
    OrgQualitativeCharacteristic,
    RegionComplianceItemLink,
    InfrastructureProviderCharacteristicLink,
    RegionCharacteristicLink,
)
from huy_compliance.resource_keys import ResourceRef
from huy_compliance.schemas import (
    ComplianceExplorerFacetsOut,
    ComplianceExplorerOut,
    ComplianceExplorerRow,
    ComplianceExplorerSuggestOut,
    ComplianceExplorerSuggestion,
    ComplianceItemOut,
    TraitSummary,
)
from huy_compliance.services import catalog_service, characteristics_service
from huy_compliance.services.placement_compliance import merge_catalog_items
from huy_compliance.services.placement_traits import inherited_placement_for_agent
from huy_compliance.services.project_aggregate_compliance import aggregate_items_for_project
from huy_compliance.services.projects_client import ProjectsClient
from huy_compliance.services.registry_client import RegistryClient

CatalogMatch = Literal["has", "missing"]
TraitMatch = Literal["has", "missing"]
TraitScope = Literal["provider", "region", "any"]


def _trait_matches(
    traits: list[TraitSummary],
    trait_key: str,
    *,
    scope: TraitScope,
    match: TraitMatch,
) -> bool:
    needle = trait_key.strip().lower()
    if not needle:
        return True

    def scoped(t: TraitSummary) -> bool:
        if scope == "any":
            return True
        return t.scope == scope

    def text_match(t: TraitSummary) -> bool:
        hay = f"{t.trait_key} {t.title} {t.description or ''}".lower()
        return needle in hay

    found = any(scoped(t) and text_match(t) for t in traits)
    return found if match == "has" else not found


def _catalog_matches(
    items: list[ComplianceItemOut],
    *,
    catalog_slug: str | None,
    catalog_item_id: str | None,
    match: CatalogMatch,
) -> bool:
    if not catalog_slug and not catalog_item_id:
        return True
    if catalog_item_id:
        has = any(i.id == catalog_item_id for i in items)
    else:
        slug = (catalog_slug or "").strip().lower()
        has = any(i.slug.lower() == slug for i in items)
    return has if match == "has" else not has


def _describe_filter(
    *,
    catalog_slug: str | None,
    catalog_item_id: str | None,
    catalog_match: CatalogMatch | None,
    trait_key: str | None,
    trait_match: TraitMatch | None,
    trait_scope: TraitScope,
    resource_type: str | None,
    q: str | None = None,
    resource_key: str | None = None,
) -> str:
    parts: list[str] = []
    if resource_key:
        parts.append(f"resource {resource_key}")
    elif q:
        parts.append(f'name/project contains "{q.strip()}"')
    if catalog_slug or catalog_item_id:
        label = catalog_slug or catalog_item_id or ""
        mode = catalog_match or "missing"
        parts.append(
            f"{'with' if mode == 'has' else 'without'} catalog “{label}”"
        )
    if trait_key:
        mode = trait_match or "has"
        scope = "" if trait_scope == "any" else f" ({trait_scope} trait)"
        parts.append(
            f"{'with' if mode == 'has' else 'without'} placement trait matching “{trait_key}”{scope}"
        )
    if resource_type:
        parts.append(f"resource type {resource_type}")
    return "; ".join(parts) if parts else "all tracked resources"


def _row_matches_q(
    row: ComplianceExplorerRow,
    needle: str,
    *,
    project_slug_by_id: dict[str, str],
) -> bool:
    if not needle:
        return True
    haystacks = [
        row.name or "",
        row.project_name or "",
        row.agent_name or "",
        project_slug_by_id.get(row.project_id, ""),
        row.resource_type,
    ]
    if row.resource_type == "project":
        haystacks.append(f"project {row.project_name or ''}")
    return any(needle in h.lower() for h in haystacks if h)


async def _load_project_name_maps(
    projects: ProjectsClient, organization_id: str, assignments: list[dict[str, Any]]
) -> tuple[dict[str, str], dict[str, str]]:
    org_projects = await projects.list_organization_projects(organization_id)
    project_name_by_id: dict[str, str] = {
        p["id"]: p.get("name") or p.get("slug") or p["id"] for p in org_projects
    }
    project_slug_by_id: dict[str, str] = {p["id"]: p.get("slug") or "" for p in org_projects}
    for assignment in assignments:
        pid = assignment["project_id"]
        pname = assignment.get("project_name")
        if pname:
            project_name_by_id[pid] = pname
        pslug = assignment.get("project_slug")
        if pslug:
            project_slug_by_id[pid] = pslug
    return project_name_by_id, project_slug_by_id


async def suggest_resources(
    projects: ProjectsClient,
    *,
    organization_id: str,
    q: str,
    resource_type: str | None = None,
    limit: int = 10,
) -> ComplianceExplorerSuggestOut:
    needle = q.strip().lower()
    if not needle:
        return ComplianceExplorerSuggestOut(
            organization_id=organization_id, query=q, suggestions=[]
        )

    assignments = await projects.list_resource_assignments(organization_id)
    project_name_by_id, project_slug_by_id = await _load_project_name_maps(
        projects, organization_id, assignments
    )

    seen: set[str] = set()
    suggestions: list[ComplianceExplorerSuggestion] = []

    def consider(
        *,
        rtype: str,
        project_id: str,
        agent_id: str | None,
        name: str | None,
    ) -> None:
        if resource_type and rtype != resource_type:
            return
        ref = ResourceRef.from_parts(
            rtype, project_id=project_id, agent_id=agent_id, name=name
        )
        key = ref.key()
        if key in seen:
            return
        project_name = project_name_by_id.get(project_id)
        project_slug = project_slug_by_id.get(project_id, "")
        haystacks = [
            name or "",
            project_name or "",
            project_slug,
            rtype,
        ]
        if rtype == "project":
            haystacks.append(f"project {project_name or ''}")
        if not any(needle in h.lower() for h in haystacks if h):
            return
        seen.add(key)
        if rtype == "project":
            label = f"Project {project_name or project_slug or project_id}"
        else:
            label = f"{rtype} {name} · {project_name or project_slug}"
        suggestions.append(
            ComplianceExplorerSuggestion(
                resource_key=key,
                resource_type=rtype,  # type: ignore[arg-type]
                label=label,
                project_id=project_id,
                project_name=project_name,
                agent_id=agent_id,
                name=name,
            )
        )

    for assignment in assignments:
        rtype = assignment["resource_type"]
        if rtype == "cloud_init":
            continue
        consider(
            rtype=rtype,
            project_id=assignment["project_id"],
            agent_id=assignment.get("agent_id"),
            name=assignment.get("name"),
        )

    for project_id in project_name_by_id:
        if any(s.project_id == project_id and s.resource_type == "project" for s in suggestions):
            continue
        consider(
            rtype="project",
            project_id=project_id,
            agent_id=None,
            name=None,
        )

    suggestions.sort(key=lambda s: s.label.lower())
    return ComplianceExplorerSuggestOut(
        organization_id=organization_id,
        query=q,
        suggestions=suggestions[:limit],
    )


async def load_criticality_by_key(
    session: AsyncSession, organization_id: str
) -> dict[str, tuple[list[ComplianceItemOut], str | None]]:
    rows = (
        await session.scalars(
            select(AssetCriticalityAssignment)
            .where(AssetCriticalityAssignment.organization_id == organization_id)
            .options(selectinload(AssetCriticalityAssignment.item_links))
        )
    ).all()
    out: dict[str, tuple[list[ComplianceItemOut], str | None]] = {}
    for row in rows:
        item_ids = [link.compliance_item_id for link in row.item_links]
        items = await catalog_service._load_items_by_ids(session, organization_id, item_ids)
        out[row.resource_key] = ([catalog_service._item_out(i) for i in items], row.placement_note)
    return out


async def build_explorer(
    session: AsyncSession,
    settings: Settings,
    registry: RegistryClient,
    projects: ProjectsClient,
    *,
    organization_id: str,
    bearer_token: str,
    catalog_slug: str | None = None,
    catalog_item_id: str | None = None,
    catalog_match: CatalogMatch | None = None,
    trait_key: str | None = None,
    trait_match: TraitMatch | None = None,
    trait_scope: TraitScope = "any",
    resource_type: str | None = None,
    q: str | None = None,
    resource_key: str | None = None,
    offset: int = 0,
    page_size: int = 25,
) -> ComplianceExplorerOut:
    if catalog_slug or catalog_item_id:
        catalog_match = catalog_match or "missing"
    if trait_key:
        trait_match = trait_match or "has"

    criticality_map = await load_criticality_by_key(session, organization_id)
    assignments = await projects.list_resource_assignments(organization_id)
    project_name_by_id, project_slug_by_id = await _load_project_name_maps(
        projects, organization_id, assignments
    )

    def resolve_project_name(project_id: str, fallback: str | None = None) -> str | None:
        return project_name_by_id.get(project_id) or fallback

    agent_cache: dict[str, dict[str, Any]] = {}
    region_parent_cache: dict[str, dict[str, str | None]] = {}
    region_name_cache: dict[str, dict[str, str]] = {}

    rows: list[ComplianceExplorerRow] = []

    async def append_row(
        *,
        rtype: str,
        project_id: str,
        project_name: str | None,
        agent_id: str | None,
        name: str | None,
        inherited: list[TraitSummary],
        inherited_items: list[ComplianceItemOut] | None = None,
        aggregate_items: list[ComplianceItemOut] | None = None,
        agent: dict[str, Any] | None,
    ) -> None:
        if resource_type and rtype != resource_type:
            return
        ref = ResourceRef.from_parts(
            rtype, project_id=project_id, agent_id=agent_id, name=name
        )
        if resource_key and ref.key() != resource_key:
            return
        direct_items, placement_note = criticality_map.get(ref.key(), ([], None))
        placement_inherited = inherited_items if inherited_items is not None else []
        child_aggregate = aggregate_items if aggregate_items is not None else []
        if rtype == "project" and not child_aggregate:
            child_aggregate = await aggregate_items_for_project(
                session,
                registry,
                organization_id=organization_id,
                project_id=project_id,
                assignments=assignments,
                criticality_map=criticality_map,
                bearer_token=bearer_token,
                agent_cache=agent_cache,
                region_parent_cache=region_parent_cache,
                region_name_cache=region_name_cache,
            )
        if rtype in ("vm", "network") and agent_id and not placement_inherited:
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
        effective_items = merge_catalog_items(
            direct_items, placement_inherited, child_aggregate
        )
        if not _catalog_matches(
            effective_items,
            catalog_slug=catalog_slug,
            catalog_item_id=catalog_item_id,
            match=catalog_match or "missing",
        ):
            return
        if rtype in ("vm", "network") and trait_key:
            if not _trait_matches(
                inherited,
                trait_key,
                scope=trait_scope,
                match=trait_match or "has",
            ):
                return
        elif rtype == "project" and trait_key:
            # Projects have no placement traits — exclude from trait filters.
            return

        region_id = agent.get("region_id") if agent else None
        provider_id = agent.get("infrastructure_provider_id") if agent else None
        region_name = next(
            (t.region_name for t in inherited if t.scope == "region" and t.region_name),
            None,
        )
        rows.append(
            ComplianceExplorerRow(
                resource_type=rtype,  # type: ignore[arg-type]
                project_id=project_id,
                project_name=project_name,
                agent_id=agent_id,
                agent_name=agent.get("name") if agent else None,
                name=name,
                region_id=region_id,
                region_name=region_name,
                infrastructure_provider_id=provider_id,
                catalog_items=effective_items,
                direct_catalog_items=direct_items,
                inherited_catalog_items=placement_inherited,
                aggregate_catalog_items=child_aggregate,
                inherited_traits=inherited,
                placement_note=placement_note,
            )
        )

    for assignment in assignments:
        rtype = assignment["resource_type"]
        if rtype == "cloud_init":
            continue
        project_id = assignment["project_id"]
        project_name = resolve_project_name(project_id, assignment.get("project_name"))
        agent_id = assignment.get("agent_id")
        name = assignment["name"]
        if agent_id and rtype in ("vm", "network"):
            inherited, inherited_items, agent = await inherited_placement_for_agent(
                session,
                registry,
                organization_id=organization_id,
                agent_id=agent_id,
                bearer_token=bearer_token,
                agent_cache=agent_cache,
                region_parent_cache=region_parent_cache,
                region_name_cache=region_name_cache,
            )
        else:
            inherited, inherited_items, agent = [], [], None
        await append_row(
            rtype=rtype,
            project_id=project_id,
            project_name=project_name,
            agent_id=agent_id,
            name=name,
            inherited=inherited,
            inherited_items=inherited_items,
            agent=agent,
        )

    # Project rows: one per project that has VM/network children (or direct project assignment).
    project_ids_with_children: set[str] = {
        a["project_id"]
        for a in assignments
        if a.get("resource_type") in ("vm", "network") and a.get("agent_id")
    }
    project_ids_with_direct = {
        key.split(":", 1)[1] for key in criticality_map if key.startswith("project:")
    }
    for project_id in project_ids_with_children | project_ids_with_direct:
        if any(r.project_id == project_id and r.resource_type == "project" for r in rows):
            continue
        await append_row(
            rtype="project",
            project_id=project_id,
            project_name=resolve_project_name(project_id),
            agent_id=None,
            name=None,
            inherited=[],
            inherited_items=[],
            agent=None,
        )

    search_needle = (q or "").strip().lower()
    if search_needle:
        rows = [
            r
            for r in rows
            if _row_matches_q(r, search_needle, project_slug_by_id=project_slug_by_id)
        ]

    description = _describe_filter(
        catalog_slug=catalog_slug,
        catalog_item_id=catalog_item_id,
        catalog_match=catalog_match,
        trait_key=trait_key,
        trait_match=trait_match,
        trait_scope=trait_scope,
        resource_type=resource_type,
        q=q,
        resource_key=resource_key,
    )
    total = len(rows)
    page_start = max(0, offset)
    page_end = page_start + page_size
    page_rows = rows[page_start:page_end]

    return ComplianceExplorerOut(
        organization_id=organization_id,
        filter_description=description,
        total_matched=total,
        offset=page_start,
        page_size=page_size,
        truncated=total > page_end,
        rows=page_rows,
    )


async def build_facets(
    session: AsyncSession, organization_id: str
) -> ComplianceExplorerFacetsOut:
    catalog = await catalog_service.list_catalog(session, organization_id)
    slug_by_id = {item.id: item.slug for item in catalog}
    provider_item_ids = (
        await session.scalars(
            select(InfrastructureProviderComplianceItemLink.compliance_item_id)
            .join(InfrastructureProviderCompliance)
            .where(InfrastructureProviderCompliance.organization_id == organization_id)
        )
    ).all()
    region_item_ids = (
        await session.scalars(
            select(RegionComplianceItemLink.compliance_item_id).where(
                RegionComplianceItemLink.organization_id == organization_id
            )
        )
    ).all()
    catalog_trait_keys = {
        slug_by_id[item_id]
        for item_id in (*provider_item_ids, *region_item_ids)
        if item_id in slug_by_id
    }

    provider_characteristic_slugs = (
        await session.scalars(
            select(OrgQualitativeCharacteristic.slug)
            .join(
                InfrastructureProviderCharacteristicLink,
                InfrastructureProviderCharacteristicLink.characteristic_id
                == OrgQualitativeCharacteristic.id,
            )
            .where(
                InfrastructureProviderCharacteristicLink.organization_id == organization_id,
                OrgQualitativeCharacteristic.organization_id == organization_id,
            )
        )
    ).all()
    region_characteristic_slugs = (
        await session.scalars(
            select(OrgQualitativeCharacteristic.slug)
            .join(
                RegionCharacteristicLink,
                RegionCharacteristicLink.characteristic_id == OrgQualitativeCharacteristic.id,
            )
            .where(
                RegionCharacteristicLink.organization_id == organization_id,
                OrgQualitativeCharacteristic.organization_id == organization_id,
            )
        )
    ).all()

    qualitative_characteristics = await characteristics_service.list_characteristics(
        session, organization_id
    )
    trait_keys = sorted(
        {
            *catalog_trait_keys,
            *[s for s in (*provider_characteristic_slugs, *region_characteristic_slugs) if s],
            *[c.slug for c in qualitative_characteristics if c.slug],
        }
    )
    return ComplianceExplorerFacetsOut(
        organization_id=organization_id,
        catalog_items=catalog,
        trait_keys=trait_keys,
        qualitative_characteristics=qualitative_characteristics,
    )
