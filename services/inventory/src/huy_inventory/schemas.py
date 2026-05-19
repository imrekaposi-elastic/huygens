"""API response models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    organization_id: str
    region_id: str
    polled_at: datetime
    payload: dict[str, Any]
    config_drift: bool
    poll_error: str | None


class AgentInventorySummary(BaseModel):
    agent_id: str
    organization_id: str
    region_id: str
    polled_at: datetime | None
    config_drift: bool
    poll_error: str | None
    vm_count: int
    network_count: int
    connection_status: str | None = None


class OrganizationDashboard(BaseModel):
    organization_id: str
    agent_count: int
    vm_count: int
    network_count: int
    agents_with_drift: int
    agents_with_errors: int
    agents: list[AgentInventorySummary]
