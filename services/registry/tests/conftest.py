"""Registry test fixtures."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-minimum-32-bytes!")
os.environ.setdefault("JWT_ISSUER", "huy-iam")
os.environ.setdefault("AGENT_TOKEN_ENCRYPTION_KEY", "test-agent-token-encryption-key")
os.environ.setdefault("INVENTORY_SERVICE_TOKEN", "test-inventory-service-token")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("KAFKA_PUBLISH_ENABLED", "false")


@pytest.fixture
async def client() -> AsyncClient:
    from huy_registry.config import get_settings
    from huy_registry.main import create_app

    get_settings.cache_clear()
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
def service_headers() -> dict[str, str]:
    return {"X-Huy-Service-Token": "test-inventory-service-token"}
