"""Compliance test fixtures."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-minimum-32-bytes!")
os.environ.setdefault("JWT_ISSUER", "huy-iam")
os.environ.setdefault("CHECK_ALERT_ENABLED", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("KAFKA_PUBLISH_ENABLED", "false")


@pytest.fixture
async def client() -> AsyncClient:
    from huy_compliance.config import get_settings
    from huy_compliance.main import create_app

    get_settings.cache_clear()
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
