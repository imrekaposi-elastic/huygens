"""DNAT REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from huy_libvirt_agent.api.deps import StateDep, verify_token
from huy_libvirt_agent.api.schemas.network import DnatRuleCreate, DnatRuleResponse
from huy_libvirt_agent.services.metadata import read_metadata

router = APIRouter(
    prefix="/api/v1/networks/{vnet}/dnat",
    tags=["dnat"],
    dependencies=[Depends(verify_token)],
)


def _cidr(state: StateDep, vnet: str) -> str:
    meta = read_metadata(state.settings.data_dir / "vnets" / vnet / "metadata.json")
    return meta.get("ipv4_cidr", "192.168.122.0/24")


@router.get("", response_model=list[DnatRuleResponse], summary="List DNAT rules")
async def list_dnat(vnet: str, state: StateDep) -> list[DnatRuleResponse]:
    return state.dnat.list_rules(vnet)


@router.post(
    "",
    response_model=DnatRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add inbound DNAT rule",
)
async def create_dnat(vnet: str, body: DnatRuleCreate, state: StateDep) -> DnatRuleResponse:
    return state.dnat.add_rule(vnet, body, _cidr(state, vnet))


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove DNAT rule",
)
async def delete_dnat(vnet: str, rule_id: str, state: StateDep) -> None:
    state.dnat.delete_rule(vnet, rule_id, _cidr(state, vnet))
