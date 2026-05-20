"""Agent settings and label schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentLabels(BaseModel):
    country: str = Field(..., description="ISO 3166-1 alpha-2 country code when possible")
    city: str
    company: str


class AgentTlsInfo(BaseModel):
    enabled: bool
    scheme: str = Field(description="http or https")
    ca_fingerprint_sha256: str | None = None
    cert_dir: str | None = None


class AgentSettingsResponse(BaseModel):
    hostname: str
    version: str
    settings: AgentLabels
    libvirt_uri: str
    data_dir: str
    tls: AgentTlsInfo


class VmCountMetrics(BaseModel):
    running: int
    total: int
    by_libvirt_state: dict[str, int] = Field(default_factory=dict)


class HostMemoryMetrics(BaseModel):
    total_bytes: int
    used_bytes: int
    available_bytes: int
    usage_percent: float
    allocated_to_vms_bytes: int


class DiskMountMetrics(BaseModel):
    mount: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    usage_percent: float


class DiskIoCounters(BaseModel):
    read_bytes_total: int
    write_bytes_total: int
    read_ops_total: int
    write_ops_total: int


class NetworkCounters(BaseModel):
    bytes_sent_total: int
    bytes_recv_total: int


class HostMetricsSnapshot(BaseModel):
    collected_at: str
    libvirt_connected: bool
    vms: VmCountMetrics
    cpu_percent: float
    memory: HostMemoryMetrics
    disk: DiskMountMetrics | None = None
    disk_io: DiskIoCounters | None = None
    network: NetworkCounters | None = None
