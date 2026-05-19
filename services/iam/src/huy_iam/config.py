"""Service configuration."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/huy-iam.db",
        alias="DATABASE_URL",
    )
    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_issuer: str = Field(default="huy-iam", alias="JWT_ISSUER")
    jwt_access_ttl_seconds: int = Field(default=3600, alias="JWT_ACCESS_TTL_SECONDS")
    bootstrap_admin_username: str = Field(default="platform-admin", alias="BOOTSTRAP_ADMIN_USERNAME")
    bootstrap_admin_password: str = Field(
        default="change-me-bootstrap",
        alias="BOOTSTRAP_ADMIN_PASSWORD",
    )
    bootstrap_admin_email: str = Field(
        default="platform-admin@example.com",
        alias="BOOTSTRAP_ADMIN_EMAIL",
    )
    host: str = Field(default="127.0.0.1", alias="HUY_IAM_HOST")
    port: int = Field(default=8081, alias="HUY_IAM_PORT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
