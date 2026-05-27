from fastapi import APIRouter

from huy_compliance import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "compliance", "version": __version__}
