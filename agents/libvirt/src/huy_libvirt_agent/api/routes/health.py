"""Health and metrics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse, Response

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict:
    return {"status": "ok"}


@router.get("/readyz", summary="Readiness probe")
async def readyz(request: Request) -> dict:
    state = request.app.state.app_state
    libvirt_ok = state.libvirt.connected
    return {"status": "ok" if libvirt_ok else "degraded", "libvirt": libvirt_ok}


@router.get("/metrics", summary="Prometheus metrics", response_class=PlainTextResponse)
async def metrics(request: Request) -> Response:
    if not request.app.state.app_state.settings.metrics_enabled:
        return PlainTextResponse("", status_code=404)
    try:
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        return PlainTextResponse("# prometheus_client not available\n")
