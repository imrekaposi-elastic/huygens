"""Projects service entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI

from huy_projects import __version__
from huy_projects.api.routes import health, projects, proxy
from huy_projects.config import get_settings
from huy_projects.db import dispose_db, get_engine, init_db
from huy_projects.models import Base

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.split("///")[-1]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    init_db(settings)
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("huy_projects_started", version=__version__)
    yield
    await dispose_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Huygens Projects",
        version=__version__,
        description="Project CRUD and libvirt agent proxy (Phase 3)",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(projects.router)
    app.include_router(proxy.router)
    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "huy_projects.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
