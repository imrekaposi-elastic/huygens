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
    oidc_enabled: bool = Field(default=False, alias="OIDC_ENABLED")
    oidc_issuer: str = Field(
        default="http://127.0.0.1:8080/realms/huygens",
        alias="OIDC_ISSUER",
    )
    oidc_realm: str = Field(default="huygens", alias="OIDC_REALM")
    oidc_client_id: str = Field(default="huy-iam", alias="OIDC_CLIENT_ID")
    oidc_client_secret: str | None = Field(default="huy-iam-dev-secret", alias="OIDC_CLIENT_SECRET")
    oidc_redirect_uri: str = Field(
        default="http://127.0.0.1:8081/api/v1/auth/oidc/callback",
        alias="OIDC_REDIRECT_URI",
    )
    oidc_scopes: str = Field(default="openid profile email", alias="OIDC_SCOPES")
    oidc_post_login_redirect: str | None = Field(default=None, alias="OIDC_POST_LOGIN_REDIRECT")

    kafka_bootstrap: str = Field(
        default="kafka:9092",
        alias="KAFKA_BOOTSTRAP",
        description="Comma-separated Kafka bootstrap brokers",
    )
    kafka_client_id: str | None = Field(default=None, alias="KAFKA_CLIENT_ID")
    kafka_publish_enabled: bool = Field(default=True, alias="KAFKA_PUBLISH_ENABLED")
    iam_service_token: str = Field(
        default="dev-iam-service-token",
        alias="IAM_SERVICE_TOKEN",
    )
    ssh_gateway_service_token: str = Field(
        default="dev-ssh-gateway-service-token",
        alias="SSH_GATEWAY_SERVICE_TOKEN",
    )
    ssh_ca_encryption_key: str = Field(
        default="dev-ssh-ca-encryption-key-change-me-32",
        alias="SSH_CA_ENCRYPTION_KEY",
    )
    ssh_cert_ttl_seconds: int = Field(default=900, alias="SSH_CERT_TTL_SECONDS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
