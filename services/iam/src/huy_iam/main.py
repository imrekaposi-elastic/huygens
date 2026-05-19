"""IAM service entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI

from huy_iam import __version__
from huy_iam.api.routes import auth, health, idp_mappings, oidc, organizations, users
from huy_iam.bootstrap import bootstrap_platform_admin
from huy_iam.config import get_settings
from huy_iam.db import dispose_db, get_engine, get_session_factory, init_db
from huy_iam.models import Base

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
    async with get_session_factory()() as session:
        await bootstrap_platform_admin(session, settings)
    logger.info("huy_iam_started", version=__version__)
    yield
    await dispose_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Huygens IAM",
        version=__version__,
        description="Local auth, Keycloak OIDC, and RBAC (Phase 1a–2)",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(oidc.router)
    app.include_router(idp_mappings.org_router)
    app.include_router(idp_mappings.platform_router)
    app.include_router(idp_mappings.auth_router)
    app.include_router(organizations.router)
    app.include_router(users.router)
    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "huy_iam.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
