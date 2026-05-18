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

    agent_token: str = Field(
        validation_alias="HUY_AGENT_TOKEN",
        description="Primary API bearer token (comma-separated list also accepted)",
    )
    agent_tokens_extra: str = Field(
        default="",
        validation_alias="HUY_AGENT_TOKENS",
        description="Additional bearer tokens, comma- or newline-separated",
    )
    data_dir: Path = Path("/var/lib/huy-libvirt-agent")
    libvirt_uri: str = Field(default="qemu:///system", validation_alias="LIBVIRT_URI")
    status_poll_seconds: int = 10
    ssh_probe_timeout_seconds: float = 2.0
    image_download_timeout_seconds: int = 600
    cloud_init_validation: Literal["off", "basic", "schema"] = Field(
        default="schema",
        description="Validate cloud-init on create: off, basic (YAML/structure), schema (cloud-init)",
    )
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
    public_base_url: str | None = Field(
        default=None,
        description="Public URL for OpenAPI/Swagger (e.g. https://dommel.example.com:8765)",
    )
    cors_origins: str = Field(
        default="",
        description="Comma-separated CORS origins; empty = same-origin only",
    )
    tls_enabled: bool = False
    tls_auto_generate: bool = True
    tls_regenerate: bool = False
    tls_cert_dir: Path | None = None
    tls_cert_file: Path | None = None
    tls_key_file: Path | None = None

    @field_validator("tls_cert_dir", "tls_cert_file", "tls_key_file", mode="before")
    @classmethod
    def tls_path_from_str(cls, v: str | Path | None) -> Path | None:
        if v is None or v == "":
            return None
        return Path(v) if isinstance(v, str) else v

    @property
    def effective_tls_cert_dir(self) -> Path:
        return self.tls_cert_dir or (self.data_dir / "tls")

    @field_validator("data_dir", "wg_config_dir", mode="before")
    @classmethod
    def path_from_str(cls, v: str | Path) -> Path:
        return Path(v) if isinstance(v, str) else v

    @staticmethod
    def _parse_token_blob(blob: str) -> set[str]:
        tokens: set[str] = set()
        for part in blob.replace("\n", ",").split(","):
            token = part.strip()
            if token:
                tokens.add(token)
        return tokens

    @property
    def valid_agent_tokens(self) -> frozenset[str]:
        """All bearer tokens that authenticate API requests."""
        tokens = self._parse_token_blob(self.agent_token)
        tokens |= self._parse_token_blob(self.agent_tokens_extra)
        return frozenset(tokens)

    @property
    def cors_origin_list(self) -> list[str]:
        if not self.cors_origins.strip():
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def agent_labels(self) -> dict[str, str]:
        return {
            "country": self.agent_country,
            "city": self.agent_city,
            "company": self.agent_company,
        }

    def ensure_data_dirs(self) -> None:
        for sub in (
            "images/registry",
            "images/cache",
            "cloud-init",
            "instances",
            "vnets",
            "audit",
            "events",
        ):
            (self.data_dir / sub).mkdir(parents=True, exist_ok=True)
        if self.tls_enabled:
            self.effective_tls_cert_dir.mkdir(parents=True, exist_ok=True)


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
    tls = data.get("tls", {})
    if tls:
        if "enabled" in tls:
            overlay["tls_enabled"] = tls["enabled"]
        if "auto_generate" in tls:
            overlay["tls_auto_generate"] = tls["auto_generate"]
        if "regenerate" in tls:
            overlay["tls_regenerate"] = tls["regenerate"]
        if "cert_dir" in tls:
            overlay["tls_cert_dir"] = tls["cert_dir"]
    return overlay


@lru_cache
def get_settings() -> Settings:
    config_path = Path(os.environ.get("HUY_CONFIG_FILE", "/etc/huy-libvirt-agent/config.yaml"))
    yaml_overlay = _load_yaml_overlay(config_path) if config_path.exists() else {}
    return Settings(**yaml_overlay)
