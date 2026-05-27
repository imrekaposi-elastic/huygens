"""Shared HTTP mocks for compliance integration tests."""

from __future__ import annotations

from httpx import Response

from helpers import ORG_ID


def mock_org_projects(
    respx_module,
    *,
    projects: list[dict] | None = None,
) -> None:
    respx_module.get(
        f"http://127.0.0.1:8084/api/v1/internal/organizations/{ORG_ID}/projects"
    ).mock(return_value=Response(200, json=projects or []))


def mock_resource_assignments(respx_module, assignments: list[dict]) -> None:
    respx_module.get(
        f"http://127.0.0.1:8084/api/v1/internal/organizations/{ORG_ID}/resource-assignments"
    ).mock(return_value=Response(200, json=assignments))
