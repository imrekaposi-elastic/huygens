"""Runtime configuration for cross-service integration tests."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class StackSettings:
    iam_url: str
    registry_url: str
    inventory_url: str
    projects_url: str
    web_url: str
    username: str
    password: str
    org_id: str | None

    @classmethod
    def from_env(cls) -> StackSettings:
        return cls(
            iam_url=os.environ.get("HUY_IAM_URL", "http://127.0.0.1:8081").rstrip("/"),
            registry_url=os.environ.get("HUY_REGISTRY_URL", "http://127.0.0.1:8082").rstrip("/"),
            inventory_url=os.environ.get("HUY_INVENTORY_URL", "http://127.0.0.1:8083").rstrip("/"),
            projects_url=os.environ.get("HUY_PROJECTS_URL", "http://127.0.0.1:8084").rstrip("/"),
            web_url=os.environ.get("HUY_WEB_URL", "http://127.0.0.1:5173").rstrip("/"),
            username=os.environ.get("HUY_E2E_USER", "platform-admin"),
            password=os.environ.get("HUY_E2E_PASSWORD", "platform-admin-dev"),
            org_id=os.environ.get("HUY_E2E_ORG_ID") or None,
        )

    def service_health_urls(self) -> dict[str, str]:
        return {
            "iam": f"{self.iam_url}/health",
            "registry": f"{self.registry_url}/health",
            "inventory": f"{self.inventory_url}/health",
            "projects": f"{self.projects_url}/health",
            "web": f"{self.web_url}/health",
        }
