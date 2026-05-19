"""Registry service configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/huy-registry.db",
        alias="DATABASE_URL",
    )
    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_issuer: str = Field(default="huy-iam", alias="JWT_ISSUER")
    agent_token_encryption_key: str = Field(
        default="dev-agent-token-encryption-key-change-me",
        alias="AGENT_TOKEN_ENCRYPTION_KEY",
    )
    inventory_service_token: str = Field(
        default="dev-inventory-service-token",
        alias="INVENTORY_SERVICE_TOKEN",
    )
    projects_service_token: str | None = Field(
        default=None,
        alias="PROJECTS_SERVICE_TOKEN",
    )
    default_refresh_seconds: int = Field(default=30, ge=10, alias="DEFAULT_REFRESH_SECONDS")
    host: str = Field(default="127.0.0.1", alias="HUY_REGISTRY_HOST")
    port: int = Field(default=8082, alias="HUY_REGISTRY_PORT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
