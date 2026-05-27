"""Projects service configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/huy-projects.db",
        alias="DATABASE_URL",
    )
    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_issuer: str = Field(default="huy-iam", alias="JWT_ISSUER")
    registry_url: str = Field(default="http://127.0.0.1:8082", alias="REGISTRY_URL")
    projects_service_token: str = Field(
        default="dev-projects-service-token",
        alias="PROJECTS_SERVICE_TOKEN",
    )
    inventory_service_token: str | None = Field(
        default="dev-inventory-service-token",
        alias="INVENTORY_SERVICE_TOKEN",
    )
    host: str = Field(default="127.0.0.1", alias="HUY_PROJECTS_HOST")
    port: int = Field(default=8084, alias="HUY_PROJECTS_PORT")
    ipam_enforce: bool = Field(
        default=True,
        alias="IPAM_ENFORCE",
        description="Reject raw ipv4_cidr on network create unless platform_admin bypass",
    )
    kafka_bootstrap: str = Field(
        default="kafka:9092",
        alias="KAFKA_BOOTSTRAP",
        description="Comma-separated Kafka bootstrap brokers",
    )
    kafka_client_id: str | None = Field(default=None, alias="KAFKA_CLIENT_ID")
    kafka_publish_enabled: bool = Field(default=True, alias="KAFKA_PUBLISH_ENABLED")
    agent_token_encryption_key: str = Field(
        default="dev-agent-token-encryption-key-change-me",
        alias="AGENT_TOKEN_ENCRYPTION_KEY",
    )
    breakout_controller_url: str = Field(
        default="http://127.0.0.1:8085",
        alias="BREAKOUT_CONTROLLER_URL",
    )
    breakout_service_token: str = Field(
        default="dev-breakout-service-token",
        alias="BREAKOUT_SERVICE_TOKEN",
    )
    link_reconcile_enabled: bool = Field(default=True, alias="LINK_RECONCILE_ENABLED")
    link_reconcile_interval_seconds: int = Field(
        default=15,
        alias="LINK_RECONCILE_INTERVAL_SECONDS",
    )
    assignment_reconcile_enabled: bool = Field(
        default=True,
        alias="ASSIGNMENT_RECONCILE_ENABLED",
    )
    assignment_reconcile_interval_seconds: int = Field(
        default=60,
        alias="ASSIGNMENT_RECONCILE_INTERVAL_SECONDS",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
