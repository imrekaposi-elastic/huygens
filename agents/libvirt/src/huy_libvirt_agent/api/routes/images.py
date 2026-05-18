"""Managed base image API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from huy_libvirt_agent.api.deps import StateDep, verify_token
from huy_libvirt_agent.api.schemas.common import ErrorResponse
from huy_libvirt_agent.api.schemas.image import (
    ImageCreateRequest,
    ImageResponse,
    ImageUpdateRequest,
)
from huy_libvirt_agent.services.image_service import ImageService

router = APIRouter(
    prefix="/api/v1/images",
    tags=["images"],
    dependencies=[Depends(verify_token)],
)


def _svc(state: StateDep) -> ImageService:
    return ImageService(state)


@router.get("", response_model=list[ImageResponse], summary="List managed images")
async def list_images(state: StateDep) -> list[ImageResponse]:
    return _svc(state).list_images()


@router.get(
    "/{name}",
    response_model=ImageResponse,
    summary="Get managed image",
    responses={404: {"model": ErrorResponse}},
)
async def get_image(name: str, state: StateDep) -> ImageResponse:
    return _svc(state).get_image(name)


@router.post(
    "",
    response_model=ImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register and optionally fetch a base image",
    responses={409: {"model": ErrorResponse}},
)
async def create_image(
    body: ImageCreateRequest, request: Request, state: StateDep
) -> ImageResponse:
    rid = getattr(request.state, "request_id", None)
    return _svc(state).create_image(body, correlation_id=rid)


@router.patch(
    "/{name}",
    response_model=ImageResponse,
    summary="Update image source or refetch",
    responses={404: {"model": ErrorResponse}},
)
async def update_image(
    name: str, body: ImageUpdateRequest, request: Request, state: StateDep
) -> ImageResponse:
    rid = getattr(request.state, "request_id", None)
    return _svc(state).update_image(name, body, correlation_id=rid)


@router.delete(
    "/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete managed image",
    responses={404: {"model": ErrorResponse}},
)
async def delete_image(name: str, request: Request, state: StateDep) -> None:
    rid = getattr(request.state, "request_id", None)
    _svc(state).delete_image(name, correlation_id=rid)
