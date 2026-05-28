"""Compliance service configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/huy-compliance.db",
        alias="DATABASE_URL",
    )
    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_issuer: str = Field(default="huy-iam", alias="JWT_ISSUER")
    registry_url: str = Field(default="http://127.0.0.1:8082", alias="REGISTRY_URL")
    projects_url: str = Field(default="http://127.0.0.1:8084", alias="PROJECTS_URL")
    projects_service_token: str = Field(
        default="dev-projects-service-token",
        alias="PROJECTS_SERVICE_TOKEN",
    )
    host: str = Field(default="127.0.0.1", alias="HUY_COMPLIANCE_HOST")
    port: int = Field(default=8086, alias="HUY_COMPLIANCE_PORT")
    check_alert_interval_seconds: int = Field(default=3600, alias="CHECK_ALERT_INTERVAL_SECONDS")
    check_alert_enabled: bool = Field(default=True, alias="CHECK_ALERT_ENABLED")

    # Evidence / export artifact storage (Phase 7+). Bytes stored out-of-DB.
    object_store_kind: str = Field(default="local", alias="OBJECT_STORE_KIND")  # local|s3
    object_store_bucket: str | None = Field(default=None, alias="OBJECT_STORE_BUCKET")
    object_store_endpoint: str | None = Field(default=None, alias="OBJECT_STORE_ENDPOINT")
    object_store_region: str | None = Field(default=None, alias="OBJECT_STORE_REGION")
    object_store_access_key_id: str | None = Field(default=None, alias="OBJECT_STORE_ACCESS_KEY_ID")
    object_store_secret_access_key: str | None = Field(
        default=None, alias="OBJECT_STORE_SECRET_ACCESS_KEY"
    )
    object_store_prefix: str = Field(default="huy-compliance", alias="OBJECT_STORE_PREFIX")
    object_store_local_dir: str = Field(default="./data/object-store", alias="OBJECT_STORE_LOCAL_DIR")

    kafka_bootstrap: str = Field(
        default="kafka:9092",
        alias="KAFKA_BOOTSTRAP",
        description="Comma-separated Kafka bootstrap brokers",
    )
    kafka_client_id: str | None = Field(default=None, alias="KAFKA_CLIENT_ID")
    kafka_publish_enabled: bool = Field(default=True, alias="KAFKA_PUBLISH_ENABLED")


@lru_cache
def get_settings() -> Settings:
    return Settings()
