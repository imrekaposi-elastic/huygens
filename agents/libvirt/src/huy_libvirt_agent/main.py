"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from huy_libvirt_agent import __version__
from huy_libvirt_agent.api.errors import register_exception_handlers
from huy_libvirt_agent.api.middleware.audit import AuditMiddleware
from huy_libvirt_agent.api.middleware.request_context import RequestContextMiddleware
from huy_libvirt_agent.api.routes import agent, dnat, health, networks, vms
from huy_libvirt_agent.app_state import AppState
from huy_libvirt_agent.config import get_settings
from huy_libvirt_agent.logging_setup import configure_logging
from huy_libvirt_agent.telemetry import setup_telemetry

logger = structlog.get_logger(__name__)

OPENAPI_TAGS = [
    {"name": "agent", "description": "Agent identity and settings"},
    {"name": "vms", "description": "Virtual machine lifecycle"},
    {"name": "networks", "description": "Virtual networks and breakout"},
    {"name": "dnat", "description": "Inbound port forwarding"},
    {"name": "health", "description": "Liveness and readiness"},
]


def create_app(state: AppState | None = None) -> FastAPI:
    settings = state.settings if state else get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app_state = app.state.app_state
        try:
            app_state.libvirt.connect()
        except Exception as e:
            logger.warning("libvirt_connect_failed", error=str(e))
        await app_state.monitor.start()
        app_state.event_bus.publish(
            "huy.agent.started",
            f"/hypervisors/{app_state.hostname}",
            {"version": __version__, "labels": settings.agent_labels},
        )
        yield
        await app_state.monitor.stop()
        app_state.libvirt.close()
        app_state.event_bus.publish(
            "huy.agent.stopped",
            f"/hypervisors/{app_state.hostname}",
            {},
        )

    app = FastAPI(
        title="Huy Libvirt Agent API",
        version=__version__,
        description="KVM hypervisor agent: VMs, vnets, breakout, DNAT.",
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.openapi_enabled else None,
        lifespan=lifespan,
    )

    if state is None:
        state = AppState.from_settings(settings)
    app.state.app_state = state

    configure_logging(settings.log_level, settings.log_format)
    setup_telemetry(settings)
    structlog.contextvars.bind_contextvars(
        **{f"agent.{k}": v for k, v in settings.agent_labels.items()}
    )

    app.add_middleware(AuditMiddleware)
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(agent.router)
    app.include_router(vms.router)
    app.include_router(networks.router)
    app.include_router(dnat.router)

    FastAPIInstrumentor.instrument_app(app)

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=OPENAPI_TAGS,
        )
        schema.setdefault("components", {}).setdefault("securitySchemes", {})[
            "BearerAuth"
        ] = {
            "type": "http",
            "scheme": "bearer",
            "description": "HUY_AGENT_TOKEN",
        }
        for path, methods in schema.get("paths", {}).items():
            if path.startswith("/api/v1"):
                for method in methods.values():
                    if isinstance(method, dict):
                        method.setdefault("security", [{"BearerAuth": []}])
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi
    return app


def run() -> None:
    import uvicorn

    settings = get_settings()
    app = create_app()
    if settings.bind_uds:
        uvicorn.run(app, uds=settings.bind_uds, log_level=settings.log_level.lower())
    else:
        uvicorn.run(
            app,
            host=settings.bind_host,
            port=settings.bind_port,
            log_level=settings.log_level.lower(),
        )


if __name__ == "__main__":
    run()
