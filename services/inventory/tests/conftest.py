"""Inventory test fixtures."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-minimum-32-bytes!")
os.environ.setdefault("JWT_ISSUER", "huy-iam")
os.environ.setdefault("INVENTORY_SERVICE_TOKEN", "test-inventory-service-token")
os.environ.setdefault("REGISTRY_URL", "http://registry.test")
os.environ.setdefault("POLL_INTERVAL_SECONDS", "3600")
os.environ.setdefault("INVENTORY_POLLER_ENABLED", "false")


@pytest.fixture
async def client() -> AsyncClient:
    from huy_inventory.config import get_settings
    from huy_inventory.main import create_app

    get_settings.cache_clear()
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
