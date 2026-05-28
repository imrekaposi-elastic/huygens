"""Trace context helpers for logs and audit mirrors."""

from __future__ import annotations

from opentelemetry import trace


def current_trace_ids() -> tuple[str | None, str | None]:
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if not ctx.is_valid:
        return None, None
    return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")


def audit_log_fields() -> dict[str, str]:
    """ECS-friendly trace fields to merge into audit structlog events."""
    trace_id, transaction_id = current_trace_ids()
    fields: dict[str, str] = {}
    if trace_id:
        fields["trace.id"] = trace_id
    if transaction_id:
        fields["transaction.id"] = transaction_id
    return fields
