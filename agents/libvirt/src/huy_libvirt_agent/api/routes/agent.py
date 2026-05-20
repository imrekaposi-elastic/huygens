"""Agent info endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from huy_libvirt_agent import __version__
from huy_libvirt_agent.api.deps import StateDep, verify_token
from huy_libvirt_agent.api.schemas.agent import (
    AgentLabels,
    AgentSettingsResponse,
    AgentTlsInfo,
    HostMetricsSnapshot,
)
from huy_libvirt_agent.services.host_metrics_service import collect_host_metrics_snapshot
from huy_libvirt_agent.services.tls_manager import ca_fingerprint

router = APIRouter(
    prefix="/api/v1/agent",
    tags=["agent"],
    dependencies=[Depends(verify_token)],
)


def _tls_info(state: StateDep) -> AgentTlsInfo:
    settings = state.settings
    if not settings.tls_enabled:
        return AgentTlsInfo(enabled=False, scheme="http")
    ca_path = settings.effective_tls_cert_dir / "ca.pem"
    fp = ca_fingerprint(ca_path) if ca_path.is_file() else None
    return AgentTlsInfo(
        enabled=True,
        scheme="https",
        ca_fingerprint_sha256=fp,
        cert_dir=str(settings.effective_tls_cert_dir),
    )


@router.get(
    "",
    response_model=AgentSettingsResponse,
    summary="Get agent identity and settings",
)
async def get_agent(state: StateDep) -> AgentSettingsResponse:
    return AgentSettingsResponse(
        hostname=state.hostname,
        version=__version__,
        settings=AgentLabels(**state.settings.agent_labels),
        libvirt_uri=state.settings.libvirt_uri,
        data_dir=str(state.settings.data_dir),
        tls=_tls_info(state),
    )


@router.get(
    "/metrics",
    response_model=HostMetricsSnapshot,
    summary="Host performance snapshot",
    description="Point-in-time CPU, memory, disk, network, and VM counts for live dashboards.",
)
async def get_host_metrics(state: StateDep) -> HostMetricsSnapshot:
    return HostMetricsSnapshot.model_validate(collect_host_metrics_snapshot(state))


@router.get(
    "/tls/ca",
    response_class=PlainTextResponse,
    summary="Download agent TLS CA certificate (PEM)",
    description="Trust this CA in the control plane for HTTPS verification. Requires bearer auth.",
)
async def get_tls_ca(state: StateDep) -> PlainTextResponse:
    if not state.settings.tls_enabled:
        raise HTTPException(status_code=404, detail="TLS is not enabled")
    ca_path = state.settings.effective_tls_cert_dir / "ca.pem"
    if not ca_path.is_file():
        raise HTTPException(status_code=404, detail="CA certificate not found")
    return PlainTextResponse(
        ca_path.read_text(),
        media_type="application/x-pem-file",
    )
