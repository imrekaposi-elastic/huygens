"""Inventory service entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import uvicorn
from fastapi import FastAPI

from huy_inventory import __version__
from huy_inventory.api.routes import events, health, inventory
from huy_inventory.config import get_settings
from huy_inventory.db import dispose_db, get_engine, get_session_factory, init_db
from huy_inventory.models import Base
from huy_events import HuyKafkaProducer, KafkaSettings

from huy_inventory.services.poller_loop import InventoryPoller
from huy_inventory.services.snapshot_publish import create_kafka_producer
from huy_inventory.services.sse_kafka import InventorySseKafkaBridge

logger = structlog.get_logger(__name__)
_poller: InventoryPoller | None = None
_kafka_producer: HuyKafkaProducer | None = None
_sse_bridge: InventorySseKafkaBridge | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _poller, _kafka_producer, _sse_bridge
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.split("///")[-1]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    init_db(settings)
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    kafka_settings: KafkaSettings | None = None
    if settings.kafka_publish_enabled:
        kafka_settings = KafkaSettings(
            KAFKA_BOOTSTRAP=settings.kafka_bootstrap,
            KAFKA_CLIENT_ID=settings.kafka_client_id,
        )
        _kafka_producer = create_kafka_producer(kafka_settings)
        await _kafka_producer.start()
    if settings.kafka_sse_consumer_enabled and kafka_settings is not None:
        from huy_inventory.services.sse_hub import get_event_hub

        _sse_bridge = InventorySseKafkaBridge(kafka_settings, get_event_hub())
        await _sse_bridge.start()
    if settings.poller_enabled:
        _poller = InventoryPoller(
            settings,
            get_session_factory(),
            kafka_producer=_kafka_producer,
        )
        await _poller.start()
    logger.info(
        "huy_inventory_started",
        version=__version__,
        poll_interval=settings.poll_interval_seconds,
        poller_enabled=settings.poller_enabled,
        kafka_publish_enabled=settings.kafka_publish_enabled,
        kafka_sse_consumer_enabled=settings.kafka_sse_consumer_enabled,
    )
    yield
    if _poller is not None:
        await _poller.stop()
    if _sse_bridge is not None:
        await _sse_bridge.stop()
        _sse_bridge = None
    if _kafka_producer is not None:
        await _kafka_producer.stop()
        _kafka_producer = None
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
    app.include_router(events.router)
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
