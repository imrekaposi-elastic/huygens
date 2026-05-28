"""Structured logging — ECS JSON via shared huy_telemetry (Phase 8)."""

from __future__ import annotations

import structlog
from huy_telemetry import configure_structlog_ecs


def configure_logging(
    level: str = "INFO",
    log_format: str = "json",
    *,
    service_name: str = "huy-libvirt-agent",
) -> None:
    configure_structlog_ecs(
        service_name=service_name,
        level=level,
        log_format=log_format,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
