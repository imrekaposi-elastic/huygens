"""SQLAlchemy / PostgreSQL client tracing (service map dependencies)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from sqlalchemy import event

from huy_telemetry.env import otel_sdk_disabled

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

_sqlalchemy_instrumented = False
_PEER_POSTGRESQL = "postgresql"
_registered_engines: set[int] = set()


def instrument_sqlalchemy() -> None:
    """Enable SQLAlchemy tracing for engines created after this call."""
    global _sqlalchemy_instrumented
    if _sqlalchemy_instrumented or otel_sdk_disabled():
        return
    SQLAlchemyInstrumentor().instrument(enable_commenter=True)
    _sqlalchemy_instrumented = True


def _attach_peer_service(engine_sync: object) -> None:
    engine_id = id(engine_sync)
    if engine_id in _registered_engines:
        return
    _registered_engines.add(engine_id)

    @event.listens_for(engine_sync, "before_cursor_execute")
    def _set_db_peer_service(
        conn: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("peer.service", _PEER_POSTGRESQL)


def register_async_sqlalchemy_engine(engine: AsyncEngine) -> None:
    """Register an async engine's sync counterpart (call from init_db after create_async_engine)."""
    if otel_sdk_disabled():
        return
    instrument_sqlalchemy()
    sync_engine = engine.sync_engine
    SQLAlchemyInstrumentor().instrument(engines=[sync_engine])
    _attach_peer_service(sync_engine)
