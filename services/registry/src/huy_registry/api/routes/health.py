from fastapi import APIRouter

from huy_registry import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "huy-registry", "version": __version__}
