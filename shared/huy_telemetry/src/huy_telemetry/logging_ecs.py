"""ECS-oriented structlog configuration with trace correlation."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

import structlog

from huy_telemetry.context import current_trace_ids

_SENSITIVE_KEYS = re.compile(
    r"(password|token|private_key|user_data|ssh_key|authorization|secret)",
    re.I,
)

_service_name: str = "huygens"


def _redact_processor(
    _logger: logging.Logger, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    for key in list(event_dict.keys()):
        if _SENSITIVE_KEYS.search(key):
            event_dict[key] = "***REDACTED***"
    return event_dict


def _ecs_fields_processor(
    _logger: logging.Logger, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    event_dict.setdefault("service.name", _service_name)
    if "log.level" not in event_dict and "level" in event_dict:
        event_dict["log.level"] = event_dict["level"]
    if "@timestamp" not in event_dict:
        event_dict["@timestamp"] = datetime.now(UTC).isoformat()
    trace_id, transaction_id = current_trace_ids()
    if trace_id:
        event_dict.setdefault("trace.id", trace_id)
    if transaction_id:
        event_dict.setdefault("transaction.id", transaction_id)
    return event_dict


def configure_structlog_ecs(
    *,
    service_name: str,
    level: str = "INFO",
    log_format: str = "json",
) -> None:
    """Configure structlog for JSON logs with ECS-style correlation fields."""
    global _service_name
    _service_name = service_name

    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact_processor,
        _ecs_fields_processor,
        structlog.processors.StackInfoRenderer(),
    ]
    if log_format == "console":
        shared.append(structlog.dev.ConsoleRenderer())
    else:
        shared.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=shared,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
