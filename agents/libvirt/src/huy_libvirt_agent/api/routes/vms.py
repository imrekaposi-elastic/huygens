"""VM REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from huy_libvirt_agent.api.deps import ActorDep, StateDep, verify_token
from huy_libvirt_agent.api.schemas.common import ErrorResponse
from huy_libvirt_agent.api.schemas.vm import VMCreateRequest, VMPatchRequest, VMResponse
from huy_libvirt_agent.services.vm_service import VMService

router = APIRouter(
    prefix="/api/v1/vms",
    tags=["vms"],
    dependencies=[Depends(verify_token)],
)


def _svc(state: StateDep) -> VMService:
    return VMService(state)


@router.get(
    "",
    response_model=list[VMResponse],
    summary="List virtual machines",
)
async def list_vms(state: StateDep) -> list[VMResponse]:
    return _svc(state).list_vms()


@router.get(
    "/{name}",
    response_model=VMResponse,
    summary="Get virtual machine",
    responses={404: {"model": ErrorResponse}},
)
async def get_vm(name: str, state: StateDep) -> VMResponse:
    return _svc(state).get_vm(name)


@router.post(
    "",
    response_model=VMResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create virtual machine from image and cloud-init",
    responses={409: {"model": ErrorResponse}},
)
async def create_vm(
    body: VMCreateRequest,
    request: Request,
    state: StateDep,
    _actor: ActorDep,
) -> VMResponse:
    rid = getattr(request.state, "request_id", None)
    return _svc(state).create_vm(body, correlation_id=rid)


@router.patch(
    "/{name}",
    response_model=VMResponse,
    summary="Modify virtual machine",
)
async def patch_vm(name: str, body: VMPatchRequest, state: StateDep) -> VMResponse:
    return _svc(state).patch_vm(name, body)


@router.delete(
    "/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete virtual machine",
)
async def delete_vm(name: str, request: Request, state: StateDep) -> None:
    rid = getattr(request.state, "request_id", None)
    _svc(state).delete_vm(name, correlation_id=rid)
