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


class VmInventoryItem(BaseModel):
    name: str | None = None
    state: str | None = None
    libvirt_state: str | None = None
    guest_status: str | None = None
    memory_mib: int | None = None
    ips: list[str] = []
    networks: list[str] = []
    orphaned: bool = True
    project_id: str | None = None
    project_name: str | None = None
    project_slug: str | None = None


class NetworkInventoryItem(BaseModel):
    name: str | None = None
    active: bool | None = None
    readonly: bool | None = None
    bridge: str | None = None
    system: bool = False
    orphaned: bool = True
    project_id: str | None = None
    project_name: str | None = None
    project_slug: str | None = None


class AgentInventorySummary(BaseModel):
    agent_id: str
    agent_name: str | None = None
    organization_id: str
    region_id: str
    polled_at: datetime | None
    config_drift: bool
    poll_error: str | None
    vm_count: int
    network_count: int
    connection_status: str | None = None
    vms: list[VmInventoryItem] = []
    networks: list[NetworkInventoryItem] = []
    orphaned_vm_count: int = 0
    orphaned_network_count: int = 0


class OrganizationDashboard(BaseModel):
    organization_id: str
    agent_count: int
    vm_count: int
    network_count: int
    agents_with_drift: int
    agents_with_errors: int
    agents: list[AgentInventorySummary]
