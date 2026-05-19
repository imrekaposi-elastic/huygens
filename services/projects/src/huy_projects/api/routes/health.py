from fastapi import APIRouter

from huy_projects import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "huy-projects", "version": __version__}
