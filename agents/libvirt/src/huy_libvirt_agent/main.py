"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from huy_telemetry import attach_fastapi_telemetry

from huy_libvirt_agent import __version__
from huy_libvirt_agent.api.errors import register_exception_handlers
from huy_libvirt_agent.api.middleware.audit import AuditMiddleware
from huy_libvirt_agent.api.routes import agent, cloud_init, dnat, health, images, networks, ssh, vms
from huy_libvirt_agent.services.ssh_relay import start_relay_server
from huy_libvirt_agent.app_state import AppState
from huy_libvirt_agent.config import get_settings
from huy_libvirt_agent.openapi_servers import openapi_servers
from huy_libvirt_agent.logging_setup import configure_logging
from huy_libvirt_agent.services.prometheus_metrics import (
    bind_metrics_state,
    register_metrics_collector,
)
from huy_libvirt_agent.services.cloudinit_requirements import (
    assert_cloud_init_available,
    cloud_init_schema_available,
)
from huy_libvirt_agent.services.tls_manager import ensure_tls_material
from huy_libvirt_agent.services.otel_metrics_sync import sync_hypervisor_metrics_to_otel
from huy_libvirt_agent.telemetry import setup_telemetry

logger = structlog.get_logger(__name__)
_otel_metrics_task: asyncio.Task | None = None
_ssh_relay_server = None

OPENAPI_TAGS = [
    {"name": "agent", "description": "Agent identity and settings"},
    {"name": "images", "description": "Managed base images (qcow2 registry)"},
    {"name": "cloud-init", "description": "Reusable cloud-init profiles"},
    {"name": "vms", "description": "Virtual machine lifecycle"},
    {"name": "networks", "description": "Virtual networks and breakout"},
    {"name": "dnat", "description": "Inbound port forwarding"},
    {"name": "health", "description": "Liveness and readiness"},
]


async def _otel_metrics_loop(app_state: AppState, interval_seconds: int) -> None:
    while True:
        try:
            sync_hypervisor_metrics_to_otel(app_state)
        except Exception as exc:  # noqa: BLE001
            logger.warning("otel_metrics_sync_failed", error=str(exc))
        await asyncio.sleep(interval_seconds)


def create_app(state: AppState | None = None) -> FastAPI:
    settings = state.settings if state else get_settings()
    otel_export_enabled = setup_telemetry(settings)
    configure_logging(
        settings.log_level,
        settings.log_format,
        service_name=settings.otel_service_name,
    )
    structlog.contextvars.bind_contextvars(
        **{f"agent.{k}": v for k, v in settings.agent_labels.items()}
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global _otel_metrics_task, _ssh_relay_server
        app_state = app.state.app_state
        if settings.cloud_init_validation == "schema":
            if cloud_init_schema_available():
                logger.info("cloud_init_schema_validation_enabled")
            else:
                logger.error("cloud_init_not_installed")
                assert_cloud_init_available()
        try:
            if app_state.libvirt is not None:
                app_state.libvirt.connect()
                logger.info(
                    "libvirt_dual_io_started",
                    write_workers=settings.libvirt_queue_workers,
                    read_workers=settings.libvirt_read_queue_workers,
                    write_max_pending=settings.libvirt_queue_max_pending,
                    read_max_pending=settings.libvirt_read_queue_max_pending,
                )
        except Exception as e:
            logger.warning("libvirt_connect_failed", error=str(e))
        await app_state.monitor.start()
        if otel_export_enabled and settings.metrics_enabled:
            sync_hypervisor_metrics_to_otel(app_state)
            _otel_metrics_task = asyncio.create_task(
                _otel_metrics_loop(app_state, settings.status_poll_seconds)
            )
        app_state.event_bus.publish(
            "huy.agent.started",
            f"/hypervisors/{app_state.hostname}",
            {"version": __version__, "labels": settings.agent_labels},
        )
        if settings.ssh_relay_enabled and settings.ssh_gateway_service_token:
            _ssh_relay_server = await start_relay_server(
                host=settings.ssh_relay_bind,
                port=settings.ssh_relay_port,
                secret=settings.ssh_gateway_service_token,
                agent_id=settings.agent_id,
            )
        yield
        if _ssh_relay_server is not None:
            _ssh_relay_server.close()
            await _ssh_relay_server.wait_closed()
            _ssh_relay_server = None
        if _otel_metrics_task is not None:
            _otel_metrics_task.cancel()
            try:
                await _otel_metrics_task
            except asyncio.CancelledError:
                pass
            _otel_metrics_task = None
        await app_state.monitor.stop()
        if app_state.libvirt is not None:
            app_state.libvirt.close()
        if app_state.libvirt_read_queue is not None:
            app_state.libvirt_read_queue.shutdown()
        if app_state.libvirt_write_queue is not None:
            app_state.libvirt_write_queue.shutdown()
        app_state.event_bus.publish(
            "huy.agent.stopped",
            f"/hypervisors/{app_state.hostname}",
            {},
        )

    app = FastAPI(
        title="Huy Libvirt Agent API",
        version=__version__,
        description="KVM hypervisor agent: images, cloud-init, VMs, vnets, breakout, DNAT.",
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.openapi_enabled else None,
        lifespan=lifespan,
    )

    if state is None:
        state = AppState.from_settings(settings)
    app.state.app_state = state
    bind_metrics_state(state)
    if settings.metrics_enabled:
        register_metrics_collector()

    cors_origins = settings.cors_origin_list
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.add_middleware(AuditMiddleware)
    attach_fastapi_telemetry(app, export_enabled=otel_export_enabled)
    app.state.otel_export_enabled = otel_export_enabled
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(agent.router)
    app.include_router(images.router)
    app.include_router(cloud_init.router)
    app.include_router(vms.router)
    app.include_router(ssh.router)
    app.include_router(networks.router)
    app.include_router(dnat.router)

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
        if not settings.bind_uds:
            schema["servers"] = openapi_servers(settings)
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi
    return app


def _uvicorn_ssl_kwargs(settings) -> dict:
    if not settings.tls_enabled or settings.bind_uds:
        if settings.tls_enabled and settings.bind_uds:
            logger.warning("tls_ignored_for_unix_socket", uds=settings.bind_uds)
        return {}
    if settings.tls_cert_file and settings.tls_key_file:
        cert_file = str(settings.tls_cert_file)
        key_file = str(settings.tls_key_file)
    else:
        import socket

        material = ensure_tls_material(
            settings.effective_tls_cert_dir,
            socket.gethostname(),
            auto_generate=settings.tls_auto_generate,
            regenerate=settings.tls_regenerate,
        )
        cert_file = str(material.server_cert)
        key_file = str(material.server_key)
        from huy_libvirt_agent.services.tls_manager import ca_fingerprint

        logger.info(
            "tls_enabled",
            cert_file=cert_file,
            ca_fingerprint=ca_fingerprint(material.ca_cert),
        )
    return {"ssl_certfile": cert_file, "ssl_keyfile": key_file}


def run() -> None:
    import uvicorn

    settings = get_settings()
    settings.ensure_data_dirs()
    app = create_app()
    ssl_kwargs = _uvicorn_ssl_kwargs(settings)
    if settings.bind_uds:
        uvicorn.run(
            app,
            uds=settings.bind_uds,
            log_level=settings.log_level.lower(),
            **ssl_kwargs,
        )
    else:
        uvicorn.run(
            app,
            host=settings.bind_host,
            port=settings.bind_port,
            log_level=settings.log_level.lower(),
            **ssl_kwargs,
        )


if __name__ == "__main__":
    run()
