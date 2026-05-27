"""Network link CRUD and topology graph."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_projects.libvirt_system import is_system_network
from huy_projects.models import IpAllocation, NetworkLink, Project, ProjectResource
from huy_projects.schemas import (
    NetworkLinkCreate,
    NetworkLinkEndpoint,
    NetworkLinkOut,
    TopologyLinkEdge,
    TopologyOut,
    TopologyVnetNode,
)
from huy_projects.services import ipam_service, link_secrets, project_service, wireguard_keys
from huy_projects.services.link_local import LOCAL_LINK_POOL_ID
from huy_projects.config import Settings

_LOCAL_TUNNEL_LABEL = "direct"


def _endpoint_key(agent_id: str, project_id: str, network_name: str) -> tuple[str, str, str]:
    return (agent_id, project_id, network_name)


def link_to_out(link: NetworkLink) -> NetworkLinkOut:
    return NetworkLinkOut(
        id=link.id,
        organization_id=link.organization_id,
        name=link.name,
        status=link.status,  # type: ignore[arg-type]
        link_type=link.link_type,  # type: ignore[arg-type]
        left=NetworkLinkEndpoint(
            agent_id=link.left_agent_id,
            project_id=link.left_project_id,
            network_name=link.left_network_name,
        ),
        right=NetworkLinkEndpoint(
            agent_id=link.right_agent_id,
            project_id=link.right_project_id,
            network_name=link.right_network_name,
        ),
        overlay_pool_id=link.overlay_pool_id,
        tunnel_cidr=link.tunnel_cidr,
        left_tunnel_address=link.left_tunnel_address,
        right_tunnel_address=link.right_tunnel_address,
        left_public_key=link.left_public_key,
        right_public_key=link.right_public_key,
        left_vnet_cidr=link.left_vnet_cidr,
        right_vnet_cidr=link.right_vnet_cidr,
        config_drift=link.config_drift,
        last_error=link.last_error,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


async def _find_duplicate_link(
    session: AsyncSession,
    organization_id: str,
    left: NetworkLinkEndpoint,
    right: NetworkLinkEndpoint,
) -> NetworkLink | None:
    lk = _endpoint_key(left.agent_id, left.project_id, left.network_name)
    rk = _endpoint_key(right.agent_id, right.project_id, right.network_name)
    result = await session.execute(
        select(NetworkLink).where(
            NetworkLink.organization_id == organization_id,
            NetworkLink.status != "deleting",
            or_(
                (
                    (NetworkLink.left_agent_id == lk[0])
                    & (NetworkLink.left_project_id == lk[1])
                    & (NetworkLink.left_network_name == lk[2])
                    & (NetworkLink.right_agent_id == rk[0])
                    & (NetworkLink.right_project_id == rk[1])
                    & (NetworkLink.right_network_name == rk[2])
                ),
                (
                    (NetworkLink.left_agent_id == rk[0])
                    & (NetworkLink.left_project_id == rk[1])
                    & (NetworkLink.left_network_name == rk[2])
                    & (NetworkLink.right_agent_id == lk[0])
                    & (NetworkLink.right_project_id == lk[1])
                    & (NetworkLink.right_network_name == lk[2])
                ),
            ),
        )
    )
    return result.scalar_one_or_none()


async def _resolve_vnet_cidr(
    session: AsyncSession, project_id: str, network_name: str
) -> str | None:
    result = await session.execute(
        select(IpAllocation.cidr).where(
            IpAllocation.project_id == project_id,
            IpAllocation.network_name == network_name,
            IpAllocation.status == "allocated",
        )
    )
    row = result.first()
    if row is not None:
        return row[0]
    resource = await session.execute(
        select(ProjectResource.desired_state).where(
            ProjectResource.project_id == project_id,
            ProjectResource.resource_type == "network",
            ProjectResource.name == network_name,
        )
    )
    desired = resource.scalar_one_or_none()
    if desired and isinstance(desired, dict):
        cidr = desired.get("ipv4_cidr")
        return str(cidr) if cidr else None
    return None


async def _validate_endpoint(
    session: AsyncSession,
    organization_id: str,
    endpoint: NetworkLinkEndpoint,
) -> Project:
    if is_system_network(endpoint.network_name):
        raise HTTPException(status_code=400, detail="Cannot link system network 'default'")
    project = await project_service.get_project(session, endpoint.project_id)
    if project is None or project.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Project not found")
    assignment = await session.execute(
        select(ProjectResource).where(
            ProjectResource.project_id == endpoint.project_id,
            ProjectResource.agent_id == endpoint.agent_id,
            ProjectResource.resource_type == "network",
            ProjectResource.name == endpoint.network_name,
        )
    )
    if assignment.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=400,
            detail=f"Network '{endpoint.network_name}' is not assigned to project on agent",
        )
    return project


async def create_link(
    session: AsyncSession,
    organization_id: str,
    body: NetworkLinkCreate,
    settings: Settings,
) -> NetworkLink:
    if (
        body.left.agent_id == body.right.agent_id
        and body.left.project_id == body.right.project_id
        and body.left.network_name == body.right.network_name
    ):
        raise HTTPException(status_code=400, detail="Cannot link identical endpoints")

    await _validate_endpoint(session, organization_id, body.left)
    await _validate_endpoint(session, organization_id, body.right)

    if await _find_duplicate_link(session, organization_id, body.left, body.right) is not None:
        raise HTTPException(status_code=409, detail="Link between these endpoints already exists")

    left_vnet_cidr = await _resolve_vnet_cidr(
        session, body.left.project_id, body.left.network_name
    )
    right_vnet_cidr = await _resolve_vnet_cidr(
        session, body.right.project_id, body.right.network_name
    )

    same_agent = body.left.agent_id == body.right.agent_id
    if same_agent:
        if not left_vnet_cidr or not right_vnet_cidr:
            raise HTTPException(
                status_code=400,
                detail="Both networks need an IPv4 CIDR (IPAM allocation or network create) for local routing",
            )
        empty_key = link_secrets.encrypt_private_key("", settings)
        link = NetworkLink(
            organization_id=organization_id,
            name=body.name,
            status="pending",
            link_type="local",
            left_agent_id=body.left.agent_id,
            left_project_id=body.left.project_id,
            left_network_name=body.left.network_name,
            right_agent_id=body.right.agent_id,
            right_project_id=body.right.project_id,
            right_network_name=body.right.network_name,
            overlay_pool_id=LOCAL_LINK_POOL_ID,
            tunnel_cidr=_LOCAL_TUNNEL_LABEL,
            left_tunnel_address=left_vnet_cidr,
            right_tunnel_address=right_vnet_cidr,
            left_public_key="",
            right_public_key="",
            left_private_key_enc=empty_key,
            right_private_key_enc=empty_key,
            left_vnet_cidr=left_vnet_cidr,
            right_vnet_cidr=right_vnet_cidr,
            desired_generation=1,
            applied_generation=0,
        )
    else:
        if not body.overlay_pool_id:
            raise HTTPException(
                status_code=400,
                detail="overlay_pool_id is required for links between different hypervisors",
            )
        pool = await ipam_service.get_pool(session, body.overlay_pool_id)
        if pool is None or pool.organization_id != organization_id:
            raise HTTPException(status_code=404, detail="Overlay pool not found")
        if pool.pool_kind != "overlay":
            raise HTTPException(
                status_code=400, detail="overlay_pool_id must reference an overlay pool"
            )

        tunnel_cidr, left_tunnel, right_tunnel = await ipam_service.allocate_link_tunnel(
            session, pool
        )
        left_priv, left_pub = wireguard_keys.generate_keypair()
        right_priv, right_pub = wireguard_keys.generate_keypair()

        link = NetworkLink(
            organization_id=organization_id,
            name=body.name,
            status="pending",
            link_type="wireguard",
            left_agent_id=body.left.agent_id,
            left_project_id=body.left.project_id,
            left_network_name=body.left.network_name,
            right_agent_id=body.right.agent_id,
            right_project_id=body.right.project_id,
            right_network_name=body.right.network_name,
            overlay_pool_id=pool.id,
            tunnel_cidr=tunnel_cidr,
            left_tunnel_address=left_tunnel,
            right_tunnel_address=right_tunnel,
            left_public_key=left_pub,
            right_public_key=right_pub,
            left_private_key_enc=link_secrets.encrypt_private_key(left_priv, settings),
            right_private_key_enc=link_secrets.encrypt_private_key(right_priv, settings),
            left_vnet_cidr=left_vnet_cidr,
            right_vnet_cidr=right_vnet_cidr,
            desired_generation=1,
            applied_generation=0,
        )
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link


async def get_link(session: AsyncSession, organization_id: str, link_id: str) -> NetworkLink | None:
    link = await session.get(NetworkLink, link_id)
    if link is None or link.organization_id != organization_id:
        return None
    return link


async def list_links(session: AsyncSession, organization_id: str) -> list[NetworkLink]:
    result = await session.execute(
        select(NetworkLink)
        .where(NetworkLink.organization_id == organization_id)
        .order_by(NetworkLink.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_link(session: AsyncSession, link: NetworkLink) -> NetworkLink:
    if link.status == "deleting":
        return link
    link.status = "deleting"
    link.desired_generation += 1
    link.applied_generation = max(0, link.applied_generation)
    await session.commit()
    await session.refresh(link)
    return link


async def build_topology(session: AsyncSession, organization_id: str) -> TopologyOut:
    result = await session.execute(
        select(
            ProjectResource.agent_id,
            ProjectResource.project_id,
            ProjectResource.name,
            Project.name,
            ProjectResource.desired_state,
        )
        .join(Project, Project.id == ProjectResource.project_id)
        .where(
            Project.organization_id == organization_id,
            ProjectResource.resource_type == "network",
        )
        .order_by(Project.name, ProjectResource.name)
    )
    vnets: list[TopologyVnetNode] = []
    for row in result.all():
        network_name = row.name
        if is_system_network(network_name):
            continue
        cidr: str | None = None
        if row.desired_state and isinstance(row.desired_state, dict):
            raw = row.desired_state.get("ipv4_cidr")
            cidr = str(raw) if raw else None
        if cidr is None:
            cidr = await _resolve_vnet_cidr(session, row.project_id, network_name)
        vnets.append(
            TopologyVnetNode(
                agent_id=row.agent_id,
                project_id=row.project_id,
                project_name=row[3],
                network_name=network_name,
                ipv4_cidr=cidr,
            )
        )

    links = await list_links(session, organization_id)
    edges = [
        TopologyLinkEdge(
            id=link.id,
            name=link.name,
            status=link.status,  # type: ignore[arg-type]
            link_type=link.link_type,  # type: ignore[arg-type]
            left=NetworkLinkEndpoint(
                agent_id=link.left_agent_id,
                project_id=link.left_project_id,
                network_name=link.left_network_name,
            ),
            right=NetworkLinkEndpoint(
                agent_id=link.right_agent_id,
                project_id=link.right_project_id,
                network_name=link.right_network_name,
            ),
            left_tunnel_address=link.left_tunnel_address,
            right_tunnel_address=link.right_tunnel_address,
            tunnel_cidr=link.tunnel_cidr,
            config_drift=link.config_drift,
            last_error=link.last_error,
        )
        for link in links
        if link.status != "deleting"
    ]
    return TopologyOut(organization_id=organization_id, vnets=vnets, links=edges)
