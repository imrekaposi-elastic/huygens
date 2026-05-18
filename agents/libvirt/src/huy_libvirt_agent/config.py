"""Application configuration via environment and YAML."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HUY_",
        extra="ignore",
        populate_by_name=True,
    )

    agent_token: str = Field(validation_alias="HUY_AGENT_TOKEN")
    data_dir: Path = Path("/var/lib/huy-libvirt-agent")
    libvirt_uri: str = Field(default="qemu:///system", validation_alias="LIBVIRT_URI")
    status_poll_seconds: int = 10
    ssh_probe_timeout_seconds: float = 2.0
    image_download_timeout_seconds: int = 600
    iptables_backend: Literal["nft", "iptables"] = "nft"
    wg_config_dir: Path = Field(default=Path("/etc/wireguard"), validation_alias="HUY_WG_CONFIG_DIR")
    default_snat_interface: str | None = None
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"
    event_bus: Literal["none", "file", "otlp", "nats"] = "file"
    audit_enabled: bool = True
    metrics_enabled: bool = True
    docs_enabled: bool = True
    openapi_enabled: bool = True
    agent_country: str = Field(validation_alias="HUY_AGENT_COUNTRY")
    agent_city: str = Field(validation_alias="HUY_AGENT_CITY")
    agent_company: str = Field(validation_alias="HUY_AGENT_COMPANY")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    otel_service_name: str = Field(default="huy-libvirt-agent", validation_alias="OTEL_SERVICE_NAME")
    bind_host: str = "127.0.0.1"
    bind_port: int = 8765
    bind_uds: str | None = None

    @field_validator("data_dir", "wg_config_dir", mode="before")
    @classmethod
    def path_from_str(cls, v: str | Path) -> Path:
        return Path(v) if isinstance(v, str) else v

    @property
    def agent_labels(self) -> dict[str, str]:
        return {
            "country": self.agent_country,
            "city": self.agent_city,
            "company": self.agent_company,
        }

    def ensure_data_dirs(self) -> None:
        for sub in ("images", "instances", "vnets", "audit", "events"):
            (self.data_dir / sub).mkdir(parents=True, exist_ok=True)


def _load_yaml_overlay(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open() as f:
        data = yaml.safe_load(f) or {}
    agent = data.get("agent", {})
    overlay: dict = {}
    if agent:
        if agent.get("country"):
            overlay["agent_country"] = agent["country"]
        if agent.get("city"):
            overlay["agent_city"] = agent["city"]
        if agent.get("company"):
            overlay["agent_company"] = agent["company"]
    for key in ("data_dir", "libvirt_uri", "event_bus", "log_level"):
        if key in data:
            overlay[key] = data[key]
    return overlay


@lru_cache
def get_settings() -> Settings:
    config_path = Path(os.environ.get("HUY_CONFIG_FILE", "/etc/huy-libvirt-agent/config.yaml"))
    yaml_overlay = _load_yaml_overlay(config_path) if config_path.exists() else {}
    return Settings(**yaml_overlay)
