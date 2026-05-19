"""Test fixtures."""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

# Set env before app imports settings.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-minimum-32-bytes!")
os.environ.setdefault("BOOTSTRAP_ADMIN_USERNAME", "platform-admin")
os.environ.setdefault("BOOTSTRAP_ADMIN_PASSWORD", "platform-admin-secret-12")

from huy_iam.config import get_settings  # noqa: E402
from huy_iam.main import create_app  # noqa: E402


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncClient:
    get_settings.cache_clear()
    app = create_app()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
