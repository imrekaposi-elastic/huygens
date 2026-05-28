"""Database engine and session."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from huy_telemetry.db import register_async_sqlalchemy_engine

from huy_registry.config import Settings

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings) -> None:
    global _engine, _session_factory
    connect_args: dict = {}
    engine_kwargs: dict = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if ":memory:" in settings.database_url:
            engine_kwargs["poolclass"] = StaticPool
    _engine = create_async_engine(
        settings.database_url,
        connect_args=connect_args,
        **engine_kwargs,
    )
    register_async_sqlalchemy_engine(_engine)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def dispose_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_engine():
    if _engine is None:
        raise RuntimeError("Database not initialized")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized")
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        yield session
