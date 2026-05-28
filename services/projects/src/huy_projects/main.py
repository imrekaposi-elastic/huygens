"""Projects service entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI
from huy_events import HuyKafkaProducer, KafkaSettings
from huy_telemetry import attach_fastapi_telemetry, prepare_service_telemetry

from huy_projects import __version__
from huy_projects.api.routes import (
    breakout_proxy,
    cloud_init_proxy,
    health,
    images_proxy,
    internal,
    ipam,
    network_links,
    projects,
    proxy,
)
from huy_projects.config import get_settings
from huy_projects.db import dispose_db, get_engine, get_session_factory, init_db
from huy_projects.db_schema import apply_schema_upgrades
from huy_projects.services.assignment_reconciler_loop import AssignmentReconcilerLoop
from huy_projects.services.link_reconciler_loop import LinkReconcilerLoop

logger = structlog.get_logger(__name__)
_link_reconciler: LinkReconcilerLoop | None = None
_assignment_reconciler: AssignmentReconcilerLoop | None = None
_kafka_producer: HuyKafkaProducer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _link_reconciler, _assignment_reconciler, _kafka_producer
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.split("///")[-1]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    init_db(settings)
    async with get_engine().begin() as conn:
        await conn.run_sync(apply_schema_upgrades)
    if settings.kafka_publish_enabled:
        kafka_settings = KafkaSettings(
            KAFKA_BOOTSTRAP=settings.kafka_bootstrap,
            KAFKA_CLIENT_ID=settings.kafka_client_id,
        )
        _kafka_producer = HuyKafkaProducer(kafka_settings, service_name="projects")
        await _kafka_producer.start()
    if settings.link_reconcile_enabled:
        _link_reconciler = LinkReconcilerLoop(
            settings,
            get_session_factory(),
            kafka_producer=_kafka_producer,
        )
        await _link_reconciler.start()
    if settings.assignment_reconcile_enabled:
        _assignment_reconciler = AssignmentReconcilerLoop(
            settings,
            get_session_factory(),
        )
        await _assignment_reconciler.start()
    logger.info(
        "huy_projects_started",
        version=__version__,
        link_reconcile_enabled=settings.link_reconcile_enabled,
        assignment_reconcile_enabled=settings.assignment_reconcile_enabled,
        kafka_publish_enabled=settings.kafka_publish_enabled,
        otel_export_enabled=getattr(app.state, "otel_export_enabled", False),
    )
    yield
    if _link_reconciler is not None:
        await _link_reconciler.stop()
        _link_reconciler = None
    if _assignment_reconciler is not None:
        await _assignment_reconciler.stop()
        _assignment_reconciler = None
    if _kafka_producer is not None:
        await _kafka_producer.stop()
        _kafka_producer = None
    await dispose_db()


def create_app() -> FastAPI:
    otel_export = prepare_service_telemetry("huy-projects")
    app = FastAPI(
        title="Huygens Projects",
        version=__version__,
        description="Project CRUD, IPAM, network links, and libvirt agent proxy (Phases 3–6)",
        lifespan=lifespan,
    )
    attach_fastapi_telemetry(app, export_enabled=otel_export)
    app.include_router(health.router)
    app.include_router(internal.router)
    app.include_router(projects.router)
    app.include_router(ipam.router)
    app.include_router(network_links.router)
    app.include_router(proxy.router)
    app.include_router(breakout_proxy.router)
    app.include_router(cloud_init_proxy.router)
    app.include_router(images_proxy.router)
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
