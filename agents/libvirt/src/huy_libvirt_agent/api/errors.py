"""HTTP exception mapping."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from huy_libvirt_agent.services.libvirt_client import LibvirtError


def register_exception_handlers(app) -> None:
    @app.exception_handler(LibvirtError)
    async def libvirt_error_handler(_request: Request, exc: LibvirtError) -> JSONResponse:
        status = 503 if exc.code in ("CONNECTION_FAILED", "NOT_CONNECTED") else 409
        if "not found" in str(exc).lower() or exc.code == "NOT_FOUND":
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
