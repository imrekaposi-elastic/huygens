"""Compliance service entrypoint."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI

from huy_compliance import __version__
from huy_compliance.api.routes import health, org_compliance, org_grc
from huy_compliance.config import get_settings
from huy_compliance.db import dispose_db, get_engine, init_db
from huy_compliance.db_schema import apply_schema_upgrades
from huy_compliance.services.check_alerter_loop import CheckAlerterLoop

logger = structlog.get_logger(__name__)
_alerter: CheckAlerterLoop | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _alerter
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.split("///")[-1]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    init_db(settings)
    async with get_engine().begin() as conn:
        await conn.run_sync(apply_schema_upgrades)
    if settings.check_alert_enabled:
        _alerter = CheckAlerterLoop(settings)
        await _alerter.start()
    logger.info("huy_compliance_started", version=__version__)
    yield
    if _alerter is not None:
        await _alerter.stop()
        _alerter = None
    await dispose_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Huygens Compliance",
        version=__version__,
        description="Compliance catalog, traits, asset criticality, explainability (Phase 7)",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(org_compliance.router)
    app.include_router(org_grc.router)
    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "huy_compliance.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
