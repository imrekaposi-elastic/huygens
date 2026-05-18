"""Structured logging with structlog and redaction."""

from __future__ import annotations

import logging
import re
from typing import Any

import structlog

SENSITIVE_KEYS = re.compile(
    r"(password|token|private_key|user_data|ssh_key|authorization|secret)",
    re.I,
)


def _redact_processor(
    _logger: logging.Logger, _method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    for key in list(event_dict.keys()):
        if SENSITIVE_KEYS.search(key):
            event_dict[key] = "***REDACTED***"
    return event_dict


def configure_logging(level: str = "INFO", log_format: str = "json") -> None:
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _redact_processor,
        structlog.processors.StackInfoRenderer(),
    ]
    if log_format == "console":
        shared.append(structlog.dev.ConsoleRenderer())
    else:
        shared.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=shared,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), logging.INFO)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
