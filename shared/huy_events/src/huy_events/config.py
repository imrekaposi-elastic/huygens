"""Kafka connection settings shared across control-plane services."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_bootstrap_servers(value: str) -> list[str]:
    servers = [s.strip() for s in value.split(",") if s.strip()]
    if not servers:
        msg = "KAFKA_BOOTSTRAP must list at least one broker (comma-separated)"
        raise ValueError(msg)
    return servers


class KafkaSettings(BaseSettings):
    """Broker list and client identity. Mix into service Settings or load standalone."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    kafka_bootstrap: str = Field(
        default="kafka:9092",
        alias="KAFKA_BOOTSTRAP",
        description="Comma-separated Kafka bootstrap brokers",
    )
    kafka_client_id: str | None = Field(default=None, alias="KAFKA_CLIENT_ID")

    @field_validator("kafka_bootstrap")
    @classmethod
    def _bootstrap_non_empty(cls, value: str) -> str:
        parse_bootstrap_servers(value)
        return value

    @property
    def bootstrap_servers(self) -> list[str]:
        return parse_bootstrap_servers(self.kafka_bootstrap)

    def resolved_client_id(self, service_name: str) -> str:
        return self.kafka_client_id or f"huy-{service_name}"
