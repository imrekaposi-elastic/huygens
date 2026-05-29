"""Projects test fixtures."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-minimum-32-bytes!")
os.environ.setdefault("JWT_ISSUER", "huy-iam")
os.environ.setdefault("PROJECTS_SERVICE_TOKEN", "test-projects-service-token")
os.environ.setdefault("INVENTORY_SERVICE_TOKEN", "test-inventory-service-token")
os.environ.setdefault("REGISTRY_URL", "http://registry.test")
os.environ.setdefault("IAM_URL", "http://iam.test")
os.environ.setdefault("IPAM_ENFORCE", "false")
os.environ.setdefault("AGENT_TOKEN_ENCRYPTION_KEY", "test-agent-token-encryption-key-32b!")
os.environ.setdefault("BREAKOUT_CONTROLLER_URL", "http://breakout.test")
os.environ.setdefault("BREAKOUT_SERVICE_TOKEN", "test-breakout-service-token")
os.environ.setdefault("LINK_RECONCILE_ENABLED", "false")
os.environ.setdefault("ASSIGNMENT_RECONCILE_ENABLED", "false")
os.environ.setdefault("KAFKA_PUBLISH_ENABLED", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")


@pytest.fixture
async def client() -> AsyncClient:
    from huy_projects.config import get_settings
    from huy_projects.main import create_app

    get_settings.cache_clear()
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
