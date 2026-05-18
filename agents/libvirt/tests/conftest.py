"""Pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Set required env before importing app modules
os.environ.setdefault("HUY_AGENT_TOKEN", "test-token")
os.environ.setdefault("HUY_AGENT_COUNTRY", "NL")
os.environ.setdefault("HUY_AGENT_CITY", "Amsterdam")
os.environ.setdefault("HUY_AGENT_COMPANY", "Huygens Test")
# Unit tests use structural validation; hypervisors should use schema + cloud-init package.
os.environ.setdefault("HUY_CLOUD_INIT_VALIDATION", "basic")


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    data.mkdir()
    os.environ["HUY_DATA_DIR"] = str(data)
    os.environ["HUY_WG_CONFIG_DIR"] = str(tmp_path / "wireguard")
    return data


@pytest.fixture
def client(tmp_data_dir: Path) -> TestClient:
    from huy_libvirt_agent.app_state import AppState
    from huy_libvirt_agent.config import get_settings
    from huy_libvirt_agent.main import create_app

    get_settings.cache_clear()
    settings = get_settings()
    state = AppState.from_settings(settings)
    app = create_app(state)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}
