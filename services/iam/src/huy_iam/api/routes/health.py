"""Health check."""

from __future__ import annotations

from fastapi import APIRouter

from huy_iam import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "huy-iam", "version": __version__}
