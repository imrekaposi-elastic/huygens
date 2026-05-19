"""Shared fixtures for cross-service integration tests (future)."""

from __future__ import annotations

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: cross-service tests requiring compose stack")


@pytest.fixture(scope="session")
def e2e_enabled() -> bool:
    return os.environ.get("HUY_E2E", "").lower() in ("1", "true", "yes")


@pytest.fixture(autouse=True)
def skip_unless_e2e(e2e_enabled: bool, request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("integration") and not e2e_enabled:
        pytest.skip("Set HUY_E2E=1 and start docker compose to run integration tests")
