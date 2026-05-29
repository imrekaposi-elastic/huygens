"""Inventory service configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/huy-inventory.db",
        alias="DATABASE_URL",
    )
    registry_url: str = Field(default="http://127.0.0.1:8082", alias="REGISTRY_URL")
    projects_url: str = Field(default="http://127.0.0.1:8084", alias="PROJECTS_URL")
    inventory_service_token: str = Field(
        default="dev-inventory-service-token",
        alias="INVENTORY_SERVICE_TOKEN",
    )
    ssh_gateway_service_token: str = Field(
        default="dev-ssh-gateway-service-token",
        alias="SSH_GATEWAY_SERVICE_TOKEN",
    )
    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_issuer: str = Field(default="huy-iam", alias="JWT_ISSUER")
    poll_interval_seconds: int = Field(default=30, ge=10, alias="POLL_INTERVAL_SECONDS")
    poller_enabled: bool = Field(default=True, alias="INVENTORY_POLLER_ENABLED")
    kafka_bootstrap: str = Field(
        default="kafka:9092",
        alias="KAFKA_BOOTSTRAP",
        description="Comma-separated Kafka bootstrap brokers",
    )
    kafka_client_id: str | None = Field(default=None, alias="KAFKA_CLIENT_ID")
    kafka_publish_enabled: bool = Field(default=True, alias="KAFKA_PUBLISH_ENABLED")
    kafka_sse_consumer_enabled: bool = Field(
        default=True,
        alias="KAFKA_SSE_CONSUMER_ENABLED",
        description="Broadcast-consume inventory snapshots for SSE (requires KAFKA_PUBLISH_ENABLED stack)",
    )
    host: str = Field(default="127.0.0.1", alias="HUY_INVENTORY_HOST")
    port: int = Field(default=8083, alias="HUY_INVENTORY_PORT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
