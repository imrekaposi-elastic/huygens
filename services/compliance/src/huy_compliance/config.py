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


@lru_cache
def get_settings() -> Settings:
    return Settings()
