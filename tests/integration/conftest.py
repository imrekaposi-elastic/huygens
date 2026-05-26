"""Shared fixtures for cross-service integration tests."""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from typing import Any

import httpx
import pytest

from http_client import ControlPlaneClient
from settings import StackSettings


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: cross-service tests requiring docker compose (HUY_E2E=1)",
    )
    config.addinivalue_line(
        "markers",
        "requires_agent: needs a connected libvirt agent in the target organization",
    )


@pytest.fixture(scope="session")
def e2e_enabled() -> bool:
    return os.environ.get("HUY_E2E", "").lower() in ("1", "true", "yes")


@pytest.fixture(autouse=True)
def skip_unless_e2e(e2e_enabled: bool, request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("integration") and not e2e_enabled:
        pytest.skip("Set HUY_E2E=1 and start docker compose to run integration tests")


@pytest.fixture(scope="session")
def stack_settings(e2e_enabled: bool) -> StackSettings:
    if not e2e_enabled:
        pytest.skip("HUY_E2E not enabled")
    return StackSettings.from_env()


@pytest.fixture(scope="session")
def http_client() -> Generator[httpx.Client, None, None]:
    with httpx.Client(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
        yield client


@pytest.fixture(scope="session")
def stack_ready(
    e2e_enabled: bool,
    stack_settings: StackSettings,
    http_client: httpx.Client,
) -> StackSettings:
    if not e2e_enabled:
        pytest.skip("HUY_E2E not enabled")
    failures: list[str] = []
    for name, url in stack_settings.service_health_urls().items():
        try:
            response = http_client.get(url)
            if response.status_code != 200:
                failures.append(f"{name}: HTTP {response.status_code} from {url}")
        except httpx.HTTPError as exc:
            failures.append(f"{name}: {exc}")
    if failures:
        pytest.fail(
            "Docker Compose stack is not reachable. Start it with:\n"
            "  docker compose up -d --build\n"
            "Failures:\n  - " + "\n  - ".join(failures),
        )
    return stack_settings


@pytest.fixture(scope="session")
def admin_token(stack_ready: StackSettings, http_client: httpx.Client) -> str:
    response = http_client.post(
        f"{stack_ready.iam_url}/api/v1/auth/login",
        json={"username": stack_ready.username, "password": stack_ready.password},
    )
    if response.status_code != 200:
        pytest.fail(
            f"Login failed ({response.status_code}): {response.text}\n"
            "Check HUY_E2E_USER / HUY_E2E_PASSWORD match compose .env bootstrap credentials.",
        )
    token = response.json().get("access_token")
    if not token:
        pytest.fail("Login response missing access_token")
    return str(token)


@pytest.fixture(scope="session")
def cp(http_client: httpx.Client, stack_ready: StackSettings, admin_token: str) -> ControlPlaneClient:
    return ControlPlaneClient(http_client, stack_ready, admin_token)


@pytest.fixture(scope="session")
def target_org_id(cp: ControlPlaneClient) -> str:
    """Organization used for read-only and agent tests (existing or first listed)."""
    if cp.stack.org_id:
        return cp.stack.org_id
    orgs = cp.iam("GET", "/api/v1/organizations").json()
    if not orgs:
        pytest.skip("No organizations in stack; create one via console setup or set HUY_E2E_ORG_ID")
    return str(orgs[0]["id"])


@pytest.fixture
def ephemeral_org(cp: ControlPlaneClient) -> Generator[dict[str, Any], None, None]:
    """Create an isolated organization and tear it down after the test."""
    slug = f"e2e-{uuid.uuid4().hex[:10]}"
    created = cp.iam(
        "POST",
        "/api/v1/organizations",
        json={"name": f"E2E {slug}", "slug": slug},
    )
    assert created.status_code == 201, created.text
    org = created.json()
    org_id = str(org["id"])
    yield org
    projects = cp.projects("GET", f"/api/v1/projects?organization_id={org_id}").json()
    for project in projects:
        deleted = cp.delete(f"{cp.stack.projects_url}/api/v1/projects/{project['id']}")
        assert deleted.status_code == 204, deleted.text
    removed = cp.delete(f"{cp.stack.iam_url}/api/v1/organizations/{org_id}")
    assert removed.status_code == 204, removed.text


@pytest.fixture
def ephemeral_project(
    cp: ControlPlaneClient,
    ephemeral_org: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    org_id = str(ephemeral_org["id"])
    slug = f"proj-{uuid.uuid4().hex[:8]}"
    created = cp.projects(
        "POST",
        "/api/v1/projects",
        json={
            "organization_id": org_id,
            "name": f"E2E Project {slug}",
            "slug": slug,
            "description": "integration test",
        },
    )
    assert created.status_code == 201, created.text
    yield created.json()
