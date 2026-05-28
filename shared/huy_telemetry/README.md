# huy-telemetry

Shared OpenTelemetry and ECS-shaped structlog for Huygens control-plane services.

See [ADR 0008](../../docs/architecture/adrs/0008-opentelemetry-and-edot.md) and [phase8-observability.md](../../docs/operations/phase8-observability.md).

```python
from huy_telemetry import (
    configure_otel,
    configure_structlog_ecs,
    instrument_fastapi,
    instrument_httpx,
    install_request_context_middleware,
)

configure_structlog_ecs(service_name="huy-registry")
configure_otel("huy-registry")
instrument_httpx()
# SQLAlchemy: call register_async_sqlalchemy_engine(engine) in init_db after create_async_engine

app = FastAPI(...)
install_request_context_middleware(app)
instrument_fastapi(app)
```

Set `OTEL_SDK_DISABLED=true` in tests. OTLP export is active only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set.
