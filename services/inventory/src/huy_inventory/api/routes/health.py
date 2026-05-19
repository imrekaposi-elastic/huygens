from fastapi import APIRouter

from huy_inventory import __version__

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "huy-inventory", "version": __version__}
