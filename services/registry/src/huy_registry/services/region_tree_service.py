"""Region hierarchy and operational coverage propagation."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from huy_registry.models import Agent, InfrastructureProvider, Region
from huy_registry.schemas import AgentOnRegionOut, InfrastructureProviderOut, RegionTreeNode


async def list_all_regions_for_provider(
    session: AsyncSession, infrastructure_provider_id: str
) -> list[Region]:
    result = await session.execute(
        select(Region)
        .where(Region.infrastructure_provider_id == infrastructure_provider_id)
        .order_by(Region.name)
    )
    return list(result.scalars().all())


async def list_agents_for_provider(
    session: AsyncSession, infrastructure_provider_id: str
) -> list[Agent]:
    result = await session.execute(
        select(Agent)
        .where(Agent.infrastructure_provider_id == infrastructure_provider_id)
        .options(selectinload(Agent.agent_technology))
    )
    return list(result.scalars().all())


def _agent_summary(agent: Agent) -> AgentOnRegionOut:
    return AgentOnRegionOut(
        id=agent.id,
        name=agent.name,
        base_url=agent.base_url,
        agent_technology_id=agent.agent_technology_id,
        agent_technology_slug=agent.agent_technology.slug,
        connection_status=agent.connection_status,  # type: ignore[arg-type]
    )


def build_region_forest(
    regions: list[Region],
    agents: list[Agent],
) -> list[RegionTreeNode]:
    agents_by_region: dict[str, list[Agent]] = defaultdict(list)
    for agent in agents:
        if agent.region_id:
            agents_by_region[agent.region_id].append(agent)

    nodes: dict[str, RegionTreeNode] = {}
    for region in regions:
        direct = agents_by_region.get(region.id, [])
        nodes[region.id] = RegionTreeNode(
            id=region.id,
            infrastructure_provider_id=region.infrastructure_provider_id,
            parent_region_id=region.parent_region_id,
            name=region.name,
            slug=region.slug,
            has_direct_agent=len(direct) > 0,
            operational=False,
            descendant_agent_count=0,
            agents=[_agent_summary(a) for a in direct],
            children=[],
        )

    roots: list[RegionTreeNode] = []
    for region in regions:
        node = nodes[region.id]
        if region.parent_region_id and region.parent_region_id in nodes:
            nodes[region.parent_region_id].children.append(node)
        else:
            roots.append(node)

    def finalize(node: RegionTreeNode, parent_operational: bool = False) -> tuple[bool, int]:
        """Coverage: direct agent, inherited from parent agent, or upward from child agents."""
        child_operational = False
        descendant_count = len(node.agents)
        for child in node.children:
            c_op, c_count = finalize(child, parent_operational or node.has_direct_agent)
            child_operational = child_operational or c_op
            descendant_count += c_count
        node.descendant_agent_count = descendant_count
        node.operational = (
            node.has_direct_agent or parent_operational or child_operational
        )
        return node.operational, descendant_count

    for root in roots:
        finalize(root, False)
    return roots


def provider_operational(forest: list[RegionTreeNode]) -> bool:
    return any(node.operational for node in forest)


def infrastructure_provider_out(
    provider: InfrastructureProvider,
    *,
    operational: bool,
    total_agents: int,
) -> InfrastructureProviderOut:
    return InfrastructureProviderOut(
        id=provider.id,
        name=provider.name,
        slug=provider.slug,
        created_at=provider.created_at,
        operational=operational,
        total_agents=total_agents,
    )


async def get_provider_with_tree(
    session: AsyncSession, infrastructure_provider_id: str
) -> tuple[InfrastructureProviderOut, list[RegionTreeNode]] | None:
    provider = await session.get(InfrastructureProvider, infrastructure_provider_id)
    if provider is None:
        return None
    regions = await list_all_regions_for_provider(session, infrastructure_provider_id)
    agents = await list_agents_for_provider(session, infrastructure_provider_id)
    forest = build_region_forest(regions, agents)
    return (
        infrastructure_provider_out(
            provider,
            operational=provider_operational(forest),
            total_agents=len(agents),
        ),
        forest,
    )
