"""Network REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from huy_libvirt_agent.api.deps import ActorDep, StateDep, verify_token
from huy_libvirt_agent.api.schemas.network import (
    BreakoutResponse,
    FlatBreakoutConfig,
    NetworkCreateRequest,
    NetworkPatchRequest,
    NetworkResponse,
    WireGuardBreakoutConfig,
)
from huy_libvirt_agent.services.metadata import read_metadata
from huy_libvirt_agent.services.network_service import NetworkService

router = APIRouter(
    prefix="/api/v1/networks",
    tags=["networks"],
    dependencies=[Depends(verify_token)],
)


def _svc(state: StateDep) -> NetworkService:
    return NetworkService(state)


def _vnet_cidr(state: StateDep, name: str) -> str:
    meta = read_metadata(state.settings.data_dir / "vnets" / name / "metadata.json")
    return meta.get("ipv4_cidr", "192.168.122.0/24")


@router.get("", response_model=list[NetworkResponse], summary="List virtual networks")
async def list_networks(state: StateDep) -> list[NetworkResponse]:
    return _svc(state).list_networks()


@router.get(
    "/{name}",
    response_model=NetworkResponse,
    summary="Get virtual network",
)
async def get_network(name: str, state: StateDep) -> NetworkResponse:
    return _svc(state).get_network(name)


@router.post(
    "",
    response_model=NetworkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create virtual network",
)
async def create_network(
    body: NetworkCreateRequest,
    request: Request,
    state: StateDep,
    _actor: ActorDep,
) -> NetworkResponse:
    rid = getattr(request.state, "request_id", None)
    return _svc(state).create_network(body, correlation_id=rid)


@router.patch("/{name}", response_model=NetworkResponse, summary="Update virtual network")
async def patch_network(
    name: str, body: NetworkPatchRequest, state: StateDep
) -> NetworkResponse:
    return _svc(state).patch_network(name, body)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete virtual network")
async def delete_network(
    name: str,
    request: Request,
    state: StateDep,
    purge: bool = Query(False),
) -> None:
    rid = getattr(request.state, "request_id", None)
    _svc(state).delete_network(name, purge=purge, correlation_id=rid)


@router.get(
    "/{name}/breakout",
    response_model=BreakoutResponse,
    summary="Get breakout configuration",
)
async def get_breakout(name: str, state: StateDep) -> BreakoutResponse:
    data = state.breakout.get_breakout(name)
    return BreakoutResponse(
        wireguard=WireGuardBreakoutConfig(**data.get("wireguard", {})),
        flat=FlatBreakoutConfig(**data.get("flat", {"enabled": False, "uplink": ""})),
    )


@router.put(
    "/{name}/breakout/wireguard",
    response_model=BreakoutResponse,
    summary="Configure WireGuard breakout",
)
async def put_wireguard_breakout(
    name: str, body: WireGuardBreakoutConfig, state: StateDep
) -> BreakoutResponse:
    cidr = _vnet_cidr(state, name)
    state.breakout.set_wireguard(name, body, cidr)
    return await get_breakout(name, state)


@router.put(
    "/{name}/breakout/flat",
    response_model=BreakoutResponse,
    summary="Configure flat L2 breakout",
)
async def put_flat_breakout(
    name: str, body: FlatBreakoutConfig, state: StateDep
) -> BreakoutResponse:
    cidr = _vnet_cidr(state, name)
    state.breakout.set_flat(name, body, cidr)
    return await get_breakout(name, state)
