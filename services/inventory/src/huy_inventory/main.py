"""Inventory service entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI

from huy_inventory import __version__
from huy_inventory.api.routes import health, inventory
from huy_inventory.config import get_settings
from huy_inventory.db import dispose_db, get_engine, get_session_factory, init_db
from huy_inventory.models import Base
from huy_inventory.services.poller_loop import InventoryPoller

logger = structlog.get_logger(__name__)
_poller: InventoryPoller | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _poller
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.split("///")[-1]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    init_db(settings)
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    if settings.poller_enabled:
        _poller = InventoryPoller(settings, get_session_factory())
        await _poller.start()
    logger.info(
        "huy_inventory_started",
        version=__version__,
        poll_interval=settings.poll_interval_seconds,
        poller_enabled=settings.poller_enabled,
    )
    yield
    if _poller is not None:
        await _poller.stop()
    await dispose_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Huygens Inventory",
        version=__version__,
        description="Agent inventory poller and dashboard API (Phase 1)",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(inventory.router)
    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "huy_inventory.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
