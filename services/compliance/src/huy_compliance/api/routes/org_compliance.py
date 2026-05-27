"""Org-scoped compliance APIs (Phase 7)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from huy_compliance.api.deps import (
    CurrentUserDep,
    ProjectsDep,
    RegistryDep,
    SessionDep,
    SettingsDep,
    TokenDep,
)
from huy_compliance.resource_keys import ResourceRef
from huy_compliance.schemas import (
    AssetCriticalityOut,
    AssetCriticalitySet,
    ComplianceCheckCreate,
    ComplianceCheckOut,
    ComplianceCheckUpdate,
    ComplianceDashboardOut,
    ComplianceExplorerFacetsOut,
    ComplianceExplorerOut,
    ComplianceExplorerSuggestOut,
    InfrastructureProviderComplianceOut,
    InfrastructureProviderComplianceSet,
    RegionComplianceOut,
    RegionComplianceSet,
    ComplianceItemCreate,
    ComplianceItemOut,
    ComplianceItemUpdate,
    PlacementRationaleOut,
    ResourceType,
    TraitCreate,
    TraitOut,
)
from huy_compliance.services import (
    authorization,
    catalog_service,
    explorer_service,
    infrastructure_compliance_service,
    rationale_service,
)
from huy_compliance.services.placement_traits import inherited_placement_for_agent
from huy_compliance.services.project_aggregate_compliance import aggregate_items_for_project

router = APIRouter(prefix="/api/v1/organizations/{organization_id}", tags=["compliance"])


@router.get("/compliance-catalog", response_model=list[ComplianceItemOut])
async def list_catalog(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[ComplianceItemOut]:
    authorization.require_compliance_read(user, organization_id)
    return await catalog_service.list_catalog(session, organization_id)


@router.post("/compliance-catalog", response_model=ComplianceItemOut, status_code=201)
async def create_catalog(
    organization_id: str,
    body: ComplianceItemCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceItemOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await catalog_service.create_catalog_item(
        session, organization_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.patch("/compliance-catalog/{item_id}", response_model=ComplianceItemOut)
async def update_catalog(
    organization_id: str,
    item_id: str,
    body: ComplianceItemUpdate,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceItemOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await catalog_service.update_catalog_item(
        session, organization_id, item_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.delete("/compliance-catalog/{item_id}", status_code=204)
async def delete_catalog(
    organization_id: str,
    item_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    authorization.require_catalog_manage(user, organization_id)
    await catalog_service.delete_catalog_item(
        session, organization_id, item_id, actor_user_id=user.user_id
    )
    await session.commit()


@router.get(
    "/infrastructure-providers/{provider_id}/compliance-profile",
    response_model=InfrastructureProviderComplianceOut,
)
async def get_provider_compliance_profile(
    organization_id: str,
    provider_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> InfrastructureProviderComplianceOut:
    authorization.require_compliance_read(user, organization_id)
    return await infrastructure_compliance_service.get_provider_compliance(
        session, organization_id, provider_id
    )


@router.put(
    "/infrastructure-providers/{provider_id}/compliance-profile",
    response_model=InfrastructureProviderComplianceOut,
)
async def set_provider_compliance_profile(
    organization_id: str,
    provider_id: str,
    body: InfrastructureProviderComplianceSet,
    user: CurrentUserDep,
    session: SessionDep,
) -> InfrastructureProviderComplianceOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await infrastructure_compliance_service.set_provider_compliance(
        session,
        organization_id,
        provider_id,
        body,
        actor_user_id=user.user_id,
    )
    await session.commit()
    return row


@router.get(
    "/regions/{region_id}/compliance-items",
    response_model=RegionComplianceOut,
)
async def get_region_compliance_items(
    organization_id: str,
    region_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> RegionComplianceOut:
    authorization.require_compliance_read(user, organization_id)
    return await infrastructure_compliance_service.get_region_compliance(
        session, organization_id, region_id
    )


@router.put(
    "/regions/{region_id}/compliance-items",
    response_model=RegionComplianceOut,
)
async def set_region_compliance_items(
    organization_id: str,
    region_id: str,
    body: RegionComplianceSet,
    user: CurrentUserDep,
    session: SessionDep,
) -> RegionComplianceOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await infrastructure_compliance_service.set_region_compliance(
        session,
        organization_id,
        region_id,
        body,
        actor_user_id=user.user_id,
    )
    await session.commit()
    return row


@router.get(
    "/infrastructure-providers/{provider_id}/traits",
    response_model=list[TraitOut],
)
async def list_provider_traits(
    organization_id: str,
    provider_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[TraitOut]:
    authorization.require_compliance_read(user, organization_id)
    return await catalog_service.list_provider_traits(session, organization_id, provider_id)


@router.post(
    "/infrastructure-providers/{provider_id}/traits",
    response_model=TraitOut,
    status_code=201,
)
async def create_provider_trait(
    organization_id: str,
    provider_id: str,
    body: TraitCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> TraitOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await catalog_service.create_provider_trait(
        session, organization_id, provider_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.delete("/traits/provider/{trait_id}", status_code=204)
async def delete_provider_trait(
    organization_id: str,
    trait_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    authorization.require_catalog_manage(user, organization_id)
    await catalog_service.delete_provider_trait(
        session, organization_id, trait_id, actor_user_id=user.user_id
    )
    await session.commit()


@router.get("/regions/{region_id}/traits", response_model=list[TraitOut])
async def list_region_traits(
    organization_id: str,
    region_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[TraitOut]:
    authorization.require_compliance_read(user, organization_id)
    return await catalog_service.list_region_traits(session, organization_id, region_id)


@router.post("/regions/{region_id}/traits", response_model=TraitOut, status_code=201)
async def create_region_trait(
    organization_id: str,
    region_id: str,
    body: TraitCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> TraitOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await catalog_service.create_region_trait(
        session, organization_id, region_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.delete("/traits/region/{trait_id}", status_code=204)
async def delete_region_trait(
    organization_id: str,
    trait_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    authorization.require_catalog_manage(user, organization_id)
    await catalog_service.delete_region_trait(
        session, organization_id, trait_id, actor_user_id=user.user_id
    )
    await session.commit()


@router.get("/compliance-checks", response_model=list[ComplianceCheckOut])
async def list_checks(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> list[ComplianceCheckOut]:
    authorization.require_compliance_read(user, organization_id)
    return await catalog_service.list_checks(session, organization_id)


@router.post("/compliance-checks", response_model=ComplianceCheckOut, status_code=201)
async def create_check(
    organization_id: str,
    body: ComplianceCheckCreate,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceCheckOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await catalog_service.create_check(
        session, organization_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.patch("/compliance-checks/{check_id}", response_model=ComplianceCheckOut)
async def update_check(
    organization_id: str,
    check_id: str,
    body: ComplianceCheckUpdate,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceCheckOut:
    authorization.require_catalog_manage(user, organization_id)
    row = await catalog_service.update_check(
        session, organization_id, check_id, body, actor_user_id=user.user_id
    )
    await session.commit()
    return row


@router.delete("/compliance-checks/{check_id}", status_code=204)
async def delete_check(
    organization_id: str,
    check_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> None:
    authorization.require_catalog_manage(user, organization_id)
    await catalog_service.delete_check(
        session, organization_id, check_id, actor_user_id=user.user_id
    )
    await session.commit()


@router.get("/compliance-explorer/facets", response_model=ComplianceExplorerFacetsOut)
async def compliance_explorer_facets(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceExplorerFacetsOut:
    authorization.require_compliance_read(user, organization_id)
    return await explorer_service.build_facets(session, organization_id)


@router.get("/compliance-explorer/suggest", response_model=ComplianceExplorerSuggestOut)
async def compliance_explorer_suggest(
    organization_id: str,
    user: CurrentUserDep,
    projects: ProjectsDep,
    q: str = Query(min_length=1, max_length=200),
    resource_type: ResourceType | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
) -> ComplianceExplorerSuggestOut:
    authorization.require_compliance_read(user, organization_id)
    return await explorer_service.suggest_resources(
        projects,
        organization_id=organization_id,
        q=q,
        resource_type=resource_type,
        limit=limit,
    )


@router.get("/compliance-explorer", response_model=ComplianceExplorerOut)
async def compliance_explorer(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
    registry: RegistryDep,
    projects: ProjectsDep,
    token: TokenDep,
    catalog_slug: str | None = Query(default=None),
    catalog_item_id: str | None = Query(default=None),
    catalog_match: explorer_service.CatalogMatch | None = Query(default=None),
    trait_key: str | None = Query(default=None),
    trait_match: explorer_service.TraitMatch | None = Query(default=None),
    trait_scope: explorer_service.TraitScope = Query(default="any"),
    resource_type: ResourceType | None = Query(default=None),
    q: str | None = Query(default=None, max_length=200),
    resource_key: str | None = Query(default=None, max_length=512),
    offset: int = Query(default=0, ge=0),
    page_size: int = Query(default=25, ge=1, le=100),
) -> ComplianceExplorerOut:
    authorization.require_compliance_read(user, organization_id)
    return await explorer_service.build_explorer(
        session,
        settings,
        registry,
        projects,
        organization_id=organization_id,
        bearer_token=token,
        catalog_slug=catalog_slug,
        catalog_item_id=catalog_item_id,
        catalog_match=catalog_match,
        trait_key=trait_key,
        trait_match=trait_match,
        trait_scope=trait_scope,
        resource_type=resource_type,
        q=q,
        resource_key=resource_key,
        offset=offset,
        page_size=page_size,
    )


@router.get("/compliance-dashboard", response_model=ComplianceDashboardOut)
async def compliance_dashboard(
    organization_id: str,
    user: CurrentUserDep,
    session: SessionDep,
) -> ComplianceDashboardOut:
    authorization.require_compliance_read(user, organization_id)
    return await catalog_service.dashboard(session, organization_id)


@router.get("/resources/{resource_type}/placement-rationale", response_model=PlacementRationaleOut)
async def placement_rationale(
    organization_id: str,
    resource_type: ResourceType,
    user: CurrentUserDep,
    session: SessionDep,
    settings: SettingsDep,
    registry: RegistryDep,
    token: TokenDep,
    project_id: str = Query(...),
    agent_id: str | None = Query(default=None),
    name: str | None = Query(default=None),
) -> PlacementRationaleOut:
    authorization.require_compliance_read(user, organization_id)
    ref = ResourceRef.from_parts(
        resource_type, project_id=project_id, agent_id=agent_id, name=name
    )
    return await rationale_service.build_placement_rationale(
        session,
        settings,
        registry,
        organization_id=organization_id,
        ref=ref,
        bearer_token=token,
    )


@router.get(
    "/projects/{project_id}/resources/{resource_type}/{name}/criticality",
    response_model=AssetCriticalityOut,
)
async def get_vm_network_criticality(
    organization_id: str,
    project_id: str,
    resource_type: ResourceType,
    name: str,
    user: CurrentUserDep,
    session: SessionDep,
    registry: RegistryDep,
    token: TokenDep,
    agent_id: str = Query(...),
) -> AssetCriticalityOut:
    authorization.require_compliance_read(user, organization_id)
    ref = ResourceRef.from_parts(
        resource_type, project_id=project_id, agent_id=agent_id, name=name
    )
    base = await catalog_service.get_asset_criticality(session, organization_id, ref)
    _, inherited_items, _ = await inherited_placement_for_agent(
        session,
        registry,
        organization_id=organization_id,
        agent_id=agent_id,
        bearer_token=token,
    )
    return base.model_copy(update={"inherited_compliance_items": inherited_items})


@router.put(
    "/projects/{project_id}/resources/{resource_type}/{name}/criticality",
    response_model=AssetCriticalityOut,
)
async def set_vm_network_criticality(
    organization_id: str,
    project_id: str,
    resource_type: ResourceType,
    name: str,
    body: AssetCriticalitySet,
    user: CurrentUserDep,
    session: SessionDep,
    registry: RegistryDep,
    token: TokenDep,
    agent_id: str = Query(...),
) -> AssetCriticalityOut:
    authorization.require_criticality_assign(user, organization_id)
    ref = ResourceRef.from_parts(
        resource_type, project_id=project_id, agent_id=agent_id, name=name
    )
    row = await catalog_service.set_asset_criticality(
        session, organization_id, ref, body, actor_user_id=user.user_id
    )
    await session.commit()
    _, inherited_items, _ = await inherited_placement_for_agent(
        session,
        registry,
        organization_id=organization_id,
        agent_id=agent_id,
        bearer_token=token,
    )
    return row.model_copy(update={"inherited_compliance_items": inherited_items})


@router.get(
    "/projects/{project_id}/criticality",
    response_model=AssetCriticalityOut,
)
async def get_project_criticality(
    organization_id: str,
    project_id: str,
    user: CurrentUserDep,
    session: SessionDep,
    registry: RegistryDep,
    projects: ProjectsDep,
    token: TokenDep,
) -> AssetCriticalityOut:
    authorization.require_compliance_read(user, organization_id)
    ref = ResourceRef.from_parts("project", project_id=project_id)
    base = await catalog_service.get_asset_criticality(session, organization_id, ref)
    criticality_map = await explorer_service.load_criticality_by_key(session, organization_id)
    assignments = await projects.list_resource_assignments(organization_id)
    aggregate = await aggregate_items_for_project(
        session,
        registry,
        organization_id=organization_id,
        project_id=project_id,
        assignments=assignments,
        criticality_map=criticality_map,
        bearer_token=token,
    )
    return base.model_copy(update={"aggregate_compliance_items": aggregate})


@router.put(
    "/projects/{project_id}/criticality",
    response_model=AssetCriticalityOut,
)
async def set_project_criticality(
    organization_id: str,
    project_id: str,
    body: AssetCriticalitySet,
    user: CurrentUserDep,
    session: SessionDep,
    registry: RegistryDep,
    projects: ProjectsDep,
    token: TokenDep,
) -> AssetCriticalityOut:
    authorization.require_criticality_assign(user, organization_id)
    ref = ResourceRef.from_parts("project", project_id=project_id)
    row = await catalog_service.set_asset_criticality(
        session, organization_id, ref, body, actor_user_id=user.user_id
    )
    await session.commit()
    criticality_map = await explorer_service.load_criticality_by_key(session, organization_id)
    assignments = await projects.list_resource_assignments(organization_id)
    aggregate = await aggregate_items_for_project(
        session,
        registry,
        organization_id=organization_id,
        project_id=project_id,
        assignments=assignments,
        criticality_map=criticality_map,
        bearer_token=token,
    )
    return row.model_copy(update={"aggregate_compliance_items": aggregate})
