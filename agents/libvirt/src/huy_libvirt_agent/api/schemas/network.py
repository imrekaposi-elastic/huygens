"""Network and breakout API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from huy_libvirt_agent.api.schemas.agent import AgentLabels


class NetworkCreateRequest(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z0-9._-]+$")
    bridge: str | None = None
    ipv4_cidr: str = Field(..., examples=["192.168.50.0/24"])
    dhcp: bool = True


class NetworkPatchRequest(BaseModel):
    autostart: bool | None = None
    ipv4_cidr: str | None = None


class WireGuardPeer(BaseModel):
    name: str
    public_key: str
    endpoint: str | None = None
    allowed_ips: list[str]


class WireGuardBreakoutConfig(BaseModel):
    enabled: bool = False
    interface: str = "wg-vnet"
    listen_port: int = 51820
    private_key: str = Field(default="", description="Key material or ref:file:/path")
    address: str = ""
    peers: list[WireGuardPeer] = Field(default_factory=list)
    vnet_routes: list[str] = Field(default_factory=list)
    nat_exempt_cidrs: list[str] = Field(default_factory=list)


class FlatBreakoutConfig(BaseModel):
    enabled: bool = False
    mode: Literal["bridge_uplink", "macvlan"] = "bridge_uplink"
    uplink: str = ""
    remote_hypervisor_cidrs: list[str] = Field(default_factory=list)
    nat_exempt_cidrs: list[str] = Field(default_factory=list)


class BreakoutResponse(BaseModel):
    wireguard: WireGuardBreakoutConfig
    flat: FlatBreakoutConfig


class NetworkResponse(BaseModel):
    name: str
    labels: AgentLabels
    uuid: str | None = None
    active: bool
    bridge: str | None = None
    ipv4_cidr: str | None = None
    dnat_rule_count: int = 0
    iptables_in_sync: bool = True


class DnatRuleCreate(BaseModel):
    public_host: str = Field(..., description="Host IP or * for all")
    public_port: int = Field(..., ge=1, le=65535)
    protocol: Literal["tcp", "udp", "both"] = "tcp"
    guest_ip: str
    guest_port: int = Field(..., ge=1, le=65535)
    comment: str | None = None


class DnatRuleResponse(BaseModel):
    rule_id: str
    labels: AgentLabels
    public_host: str
    public_port: int
    protocol: str
    guest_ip: str
    guest_port: int
    comment: str | None = None
