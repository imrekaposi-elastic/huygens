"""S3 / SeaweedFS client span attributes."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from huy_telemetry.s3 import s3_client_span


def test_s3_client_span_seaweedfs_peer(monkeypatch) -> None:
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(
        trace,
        "get_tracer",
        lambda name, *args, **kwargs: provider.get_tracer(name, *args, **kwargs),
    )

    with s3_client_span(
        "PutObject",
        bucket="huygens-dev",
        key="evidence/x",
        endpoint="http://seaweed-s3:8333",
    ):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = dict(spans[0].attributes or {})
    assert attrs.get("peer.service") == "seaweedfs"
    assert attrs.get("rpc.method") == "PutObject"
    assert attrs.get("aws.s3.bucket") == "huygens-dev"
    assert attrs.get("server.address") == "seaweed-s3:8333"
