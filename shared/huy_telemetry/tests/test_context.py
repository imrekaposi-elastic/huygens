"""Trace context helpers."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from huy_telemetry.context import audit_log_fields, current_trace_ids


def test_current_trace_ids_without_span() -> None:
    trace.set_tracer_provider(TracerProvider())
    assert current_trace_ids() == (None, None)
    assert audit_log_fields() == {}


def test_audit_log_fields_with_active_span() -> None:
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("test-span"):
        trace_id, transaction_id = current_trace_ids()
        assert trace_id is not None
        assert len(trace_id) == 32
        assert transaction_id is not None
        fields = audit_log_fields()
        assert fields["trace.id"] == trace_id
        assert fields["transaction.id"] == transaction_id
