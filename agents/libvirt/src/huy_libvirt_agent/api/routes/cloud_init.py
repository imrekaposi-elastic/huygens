"""Cloud-init profile API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from huy_libvirt_agent.api.deps import StateDep, verify_token
from huy_libvirt_agent.api.schemas.common import ErrorResponse
from huy_libvirt_agent.api.schemas.cloudinit_validation import (
    CloudInitValidateRequest,
    CloudInitValidateResponse,
)
from huy_libvirt_agent.api.schemas.image import (
    CloudInitProfileCreateRequest,
    CloudInitProfileResponse,
    CloudInitProfileUpdateRequest,
)
from huy_libvirt_agent.services.cloudinit_profile_service import CloudInitProfileService

router = APIRouter(
    prefix="/api/v1/cloud-init",
    tags=["cloud-init"],
    dependencies=[Depends(verify_token)],
)


def _svc(state: StateDep) -> CloudInitProfileService:
    return CloudInitProfileService(state)


@router.post(
    "/validate",
    response_model=CloudInitValidateResponse,
    summary="Validate cloud-init config without saving",
    responses={
        422: {
            "description": "Validation failed",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Cloud-init configuration is invalid",
                        "code": "CLOUD_INIT_INVALID",
                        "issues": [
                            {
                                "field": "user_data",
                                "path": "line 3",
                                "message": "Invalid YAML: ...",
                                "line": 3,
                            }
                        ],
                    }
                }
            },
        }
    },
)
async def validate_cloud_init(
    body: CloudInitValidateRequest, state: StateDep
) -> CloudInitValidateResponse:
    _svc(state).validate_payload(
        body.user_data,
        body.meta_data,
        body.network_config,
        body.ssh_keys,
    )
    return CloudInitValidateResponse(
        valid=True,
        mode=state.settings.cloud_init_validation,
    )


@router.get(
    "",
    response_model=list[CloudInitProfileResponse],
    summary="List cloud-init profiles",
)
async def list_profiles(state: StateDep) -> list[CloudInitProfileResponse]:
    return _svc(state).list_profiles()


@router.get(
    "/{name}",
    response_model=CloudInitProfileResponse,
    summary="Get cloud-init profile",
    responses={404: {"model": ErrorResponse}},
)
async def get_profile(name: str, state: StateDep) -> CloudInitProfileResponse:
    return _svc(state).get_profile(name)


@router.post(
    "",
    response_model=CloudInitProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create cloud-init profile",
    responses={409: {"model": ErrorResponse}},
)
async def create_profile(
    body: CloudInitProfileCreateRequest, request: Request, state: StateDep
) -> CloudInitProfileResponse:
    rid = getattr(request.state, "request_id", None)
    return _svc(state).create_profile(body, correlation_id=rid)


@router.patch(
    "/{name}",
    response_model=CloudInitProfileResponse,
    summary="Update cloud-init profile",
    responses={404: {"model": ErrorResponse}},
)
async def update_profile(
    name: str, body: CloudInitProfileUpdateRequest, request: Request, state: StateDep
) -> CloudInitProfileResponse:
    rid = getattr(request.state, "request_id", None)
    return _svc(state).update_profile(name, body, correlation_id=rid)


@router.delete(
    "/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete cloud-init profile",
    responses={404: {"model": ErrorResponse}},
)
async def delete_profile(name: str, request: Request, state: StateDep) -> None:
    rid = getattr(request.state, "request_id", None)
    _svc(state).delete_profile(name, correlation_id=rid)
