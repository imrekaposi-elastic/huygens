"""SQLAlchemy instrumentation guards."""

from __future__ import annotations

from huy_telemetry.db import instrument_sqlalchemy, register_async_sqlalchemy_engine


def test_sqlalchemy_instrumentation_noop_when_disabled(monkeypatch) -> None:
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")

    class _FakeEngine:
        sync_engine = object()

    instrument_sqlalchemy()
    register_async_sqlalchemy_engine(_FakeEngine())  # type: ignore[arg-type]
