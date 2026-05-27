"""IP pool CRUD and allocation."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_projects.ipam.core import (
    IpamError,
    hosts_to_prefixlen,
    next_subnet,
    parse_network,
    plan_subnets,
    validate_overlay_pool_cidr,
    validate_pool_cidr,
)
from huy_projects.models import IpAllocation, IpPool, NetworkLink, Project
from huy_projects.schemas import (
    IpAllocationOut,
    IpPoolCreate,
    IpPoolOut,
    WizardApplyRequest,
    WizardPlanRequest,
    WizardPlanResponse,
    WizardSubnetPlan,
)


def pool_to_out(pool: IpPool) -> IpPoolOut:
    return IpPoolOut(
        id=pool.id,
        organization_id=pool.organization_id,
        name=pool.name,
        cidr=pool.cidr,
        description=pool.description,
        exceptions=pool.exceptions or [],
        pool_kind=pool.pool_kind,  # type: ignore[arg-type]
        created_at=pool.created_at,
    )


def allocation_to_out(row: IpAllocation) -> IpAllocationOut:
    return IpAllocationOut(
        id=row.id,
        pool_id=row.pool_id,
        project_id=row.project_id,
        cidr=row.cidr,
        network_name=row.network_name,
        status=row.status,  # type: ignore[arg-type]
        created_at=row.created_at,
    )


async def get_pool(session: AsyncSession, pool_id: str) -> IpPool | None:
    return await session.get(IpPool, pool_id)


async def list_pools(session: AsyncSession, organization_id: str) -> list[IpPool]:
    result = await session.execute(
        select(IpPool).where(IpPool.organization_id == organization_id).order_by(IpPool.name)
    )
    return list(result.scalars().all())


async def create_pool(session: AsyncSession, organization_id: str, body: IpPoolCreate) -> IpPool:
    try:
        if body.pool_kind == "overlay":
            pool_net = validate_overlay_pool_cidr(body.cidr)
        else:
            pool_net = validate_pool_cidr(body.cidr)
        for exc in body.exceptions:
            exc_net = parse_network(exc)
            if not exc_net.subnet_of(pool_net):
                raise IpamError(f"Exception {exc} is not within pool {body.cidr}")
    except IpamError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    existing = await session.execute(
        select(IpPool).where(IpPool.organization_id == organization_id, IpPool.name == body.name)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Pool name already exists")

    pool = IpPool(
        organization_id=organization_id,
        name=body.name,
        cidr=body.cidr,
        description=body.description,
        exceptions=body.exceptions,
        pool_kind=body.pool_kind,
    )
    session.add(pool)
    await session.commit()
    await session.refresh(pool)
    return pool


async def delete_pool(session: AsyncSession, organization_id: str, pool_id: str) -> None:
    pool = await get_pool(session, pool_id)
    if pool is None or pool.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Pool not found")

    alloc_result = await session.execute(
        select(IpAllocation).where(
            IpAllocation.pool_id == pool_id,
            IpAllocation.status.in_(("reserved", "allocated")),
        )
    )
    allocations = list(alloc_result.scalars().all())
    if allocations:
        in_use = [a for a in allocations if a.status == "allocated" and a.network_name]
        reserved = [a for a in allocations if a.status == "reserved" or not a.network_name]
        parts: list[str] = []
        if in_use:
            nets = ", ".join(
                f"{a.network_name} ({a.cidr})" for a in in_use[:3] if a.network_name
            )
            extra = f" (+{len(in_use) - 3} more)" if len(in_use) > 3 else ""
            parts.append(f"{len(in_use)} network(s) still bound ({nets}{extra})")
        if reserved:
            parts.append(f"{len(reserved)} reserved subnet block(s)")
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete pool '{pool.name}': "
                + "; ".join(parts)
                + ". Release or delete those networks first."
            ),
        )

    link_result = await session.execute(
        select(NetworkLink).where(
            NetworkLink.overlay_pool_id == pool_id,
            NetworkLink.status != "deleting",
        )
    )
    links = list(link_result.scalars().all())
    if links:
        names = ", ".join(link.name for link in links[:3])
        extra = f" (+{len(links) - 3} more)" if len(links) > 3 else ""
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot delete pool '{pool.name}': "
                f"{len(links)} topology link(s) still use it ({names}{extra}). "
                "Delete those links in Topology first."
            ),
        )

    await session.delete(pool)
    await session.commit()


async def _occupied_cidrs(session: AsyncSession, pool_id: str) -> list[str]:
    result = await session.execute(
        select(IpAllocation.cidr).where(
            IpAllocation.pool_id == pool_id,
            IpAllocation.status.in_(("reserved", "allocated")),
        )
    )
    return [row[0] for row in result.all()]


async def allocate_subnet(
    session: AsyncSession,
    *,
    pool: IpPool,
    project: Project,
    hosts: int,
    network_name: str | None = None,
    reserve_only: bool = False,
) -> IpAllocation:
    if project.organization_id != pool.organization_id:
        raise HTTPException(status_code=400, detail="Pool and project organization mismatch")
    try:
        pool_net = validate_pool_cidr(pool.cidr)
        prefixlen = hosts_to_prefixlen(hosts)
        subnet = next_subnet(
            pool_net,
            prefixlen,
            await _occupied_cidrs(session, pool.id),
            exceptions=pool.exceptions or [],
        )
    except IpamError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    row = IpAllocation(
        pool_id=pool.id,
        project_id=project.id,
        cidr=str(subnet),
        network_name=network_name,
        status="reserved" if reserve_only else "reserved",
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def get_allocation(session: AsyncSession, allocation_id: str) -> IpAllocation | None:
    return await session.get(IpAllocation, allocation_id)


async def bind_allocation_to_network(
    session: AsyncSession, allocation: IpAllocation, network_name: str
) -> IpAllocation:
    if allocation.status == "released":
        raise HTTPException(status_code=400, detail="Allocation was released")
    allocation.network_name = network_name
    allocation.status = "allocated"
    await session.commit()
    await session.refresh(allocation)
    return allocation


async def release_allocation(session: AsyncSession, allocation: IpAllocation) -> None:
    allocation.status = "released"
    allocation.network_name = None
    await session.commit()


async def wizard_plan(session: AsyncSession, body: WizardPlanRequest) -> WizardPlanResponse:
    pool = await get_pool(session, body.pool_id)
    if pool is None:
        raise HTTPException(status_code=404, detail="Pool not found")
    try:
        cidrs = plan_subnets(
            pool.cidr,
            network_count=body.network_count,
            hosts_per_network=body.hosts_per_network,
            occupied=await _occupied_cidrs(session, pool.id),
            exceptions=(pool.exceptions or []) + body.exceptions,
        )
    except IpamError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    subnets = [
        WizardSubnetPlan(suggested_name=f"lab{i}", cidr=cidr) for i, cidr in enumerate(cidrs)
    ]
    return WizardPlanResponse(pool_id=pool.id, subnets=subnets)


async def wizard_apply(
    session: AsyncSession, project: Project, body: WizardApplyRequest
) -> list[IpAllocationOut]:
    pool = await get_pool(session, body.pool_id)
    if pool is None:
        raise HTTPException(status_code=404, detail="Pool not found")
    if project.organization_id != pool.organization_id:
        raise HTTPException(status_code=400, detail="Pool and project organization mismatch")

    created: list[IpAllocation] = []
    for entry in body.subnets:
        for existing in await _occupied_cidrs(session, pool.id):
            if existing == entry.cidr:
                raise HTTPException(status_code=409, detail=f"CIDR already allocated: {entry.cidr}")
        row = IpAllocation(
            pool_id=pool.id,
            project_id=project.id,
            cidr=entry.cidr,
            network_name=entry.name,
            status="reserved",
        )
        session.add(row)
        created.append(row)
    await session.commit()
    for row in created:
        await session.refresh(row)
    return [allocation_to_out(r) for r in created]


async def resolve_network_cidr(
    session: AsyncSession,
    project: Project,
    body: dict,
) -> tuple[dict, IpAllocation | None]:
    """Strip IPAM control fields and resolve ipv4_cidr for agent create."""
    agent_body = dict(body)
    ipam_spec = agent_body.pop("ipam", None)
    allocation_id = agent_body.pop("allocation_id", None)
    agent_body.pop("ipam_bypass", None)

    allocation: IpAllocation | None = None

    if ipam_spec is not None:
        pool_id = ipam_spec.get("pool_id")
        hosts = ipam_spec.get("hosts")
        if not pool_id or not hosts:
            raise HTTPException(status_code=400, detail="ipam requires pool_id and hosts")
        pool = await get_pool(session, pool_id)
        if pool is None:
            raise HTTPException(status_code=404, detail="Pool not found")
        allocation = await allocate_subnet(session, pool=pool, project=project, hosts=int(hosts))
        agent_body["ipv4_cidr"] = allocation.cidr
    elif allocation_id:
        allocation = await get_allocation(session, allocation_id)
        if allocation is None:
            raise HTTPException(status_code=404, detail="Allocation not found")
        if allocation.project_id != project.id:
            raise HTTPException(status_code=403, detail="Allocation belongs to another project")
        if allocation.status == "released":
            raise HTTPException(status_code=400, detail="Allocation was released")
        agent_body["ipv4_cidr"] = allocation.cidr

    return agent_body, allocation


async def _occupied_tunnel_cidrs(session: AsyncSession, pool_id: str) -> list[str]:
    result = await session.execute(
        select(NetworkLink.tunnel_cidr).where(
            NetworkLink.overlay_pool_id == pool_id,
            NetworkLink.status != "deleting",
        )
    )
    return [row[0] for row in result.all()]


async def allocate_link_tunnel(
    session: AsyncSession, pool: IpPool
) -> tuple[str, str, str]:
    """Allocate a /30 from an overlay pool; returns (tunnel_cidr, left_ip, right_ip)."""
    if pool.pool_kind != "overlay":
        raise HTTPException(status_code=400, detail="Pool must have pool_kind overlay")
    try:
        pool_net = validate_overlay_pool_cidr(pool.cidr)
        subnet = next_subnet(
            pool_net,
            30,
            await _occupied_tunnel_cidrs(session, pool.id),
            exceptions=pool.exceptions or [],
        )
        hosts = list(subnet.hosts())
        if len(hosts) < 2:
            raise IpamError("No host addresses in /30 subnet")
        return str(subnet), str(hosts[0]), str(hosts[1])
    except IpamError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
