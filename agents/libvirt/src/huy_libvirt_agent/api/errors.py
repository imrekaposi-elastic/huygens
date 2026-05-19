"""HTTP exception mapping."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from huy_libvirt_agent.services.cloudinit_validator import CloudInitValidationError
from huy_libvirt_agent.services.libvirt_client import LibvirtError


def register_exception_handlers(app) -> None:
    @app.exception_handler(LibvirtError)
    async def libvirt_error_handler(_request: Request, exc: LibvirtError) -> JSONResponse:
        code_map = {
            "NOT_FOUND": 404,
            "DOMAIN_NOT_FOUND": 404,
            "NETWORK_NOT_FOUND": 404,
            "IMAGE_NOT_READY": 409,
            "IMAGE_EXISTS": 409,
            "PROFILE_EXISTS": 409,
            "DOMAIN_EXISTS": 409,
            "NETWORK_EXISTS": 409,
            "NETWORK_READONLY": 403,
            "OPERATION_INVALID": 409,
            "XML_ERROR": 400,
            "DEFINE_FAILED": 502,
            "LIBVIRT_FAILED": 502,
            "LIBVIRT_SYSTEM_ERROR": 503,
            "CONNECTION_FAILED": 503,
            "NOT_CONNECTED": 503,
            "AUTH_FAILED": 503,
            "LIBVIRT_QUEUE_FULL": 503,
            "LIBVIRT_QUEUE_TIMEOUT": 503,
        }
        status = code_map.get(exc.code, 409)
        if "not found" in str(exc).lower():
            status = 404
        return JSONResponse(
            status_code=status,
            content={"detail": str(exc), "code": exc.code},
        )

    @app.exception_handler(FileNotFoundError)
    async def not_found_handler(_request: Request, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(PermissionError)
    async def permission_handler(_request: Request, exc: PermissionError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(CloudInitValidationError)
    async def cloud_init_validation_handler(
        _request: Request, exc: CloudInitValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": str(exc),
                "code": "CLOUD_INIT_INVALID",
                "issues": [i.as_dict() for i in exc.issues],
            },
        )
