"""Reconcile network links to agents via breakout-controller + agent proxy."""

from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_events import HuyKafkaProducer

from huy_projects.config import Settings
from huy_projects.models import NetworkLink
from huy_projects.services.agent_proxy import AgentProxy
from huy_projects.services.breakout_client import BreakoutControllerClient
from huy_projects.services.link_local import disabled_flat, disabled_wireguard, flat_local_peer
from huy_projects.services.link_publish import publish_link_event
from huy_projects.services.link_secrets import decrypt_private_key

logger = structlog.get_logger(__name__)


def _format_reconcile_error(exc: Exception) -> str:
    err = str(exc)[:2000]
    if "local_peer" in err and ("422" in err or "literal_error" in err):
        return (
            "Agent rejected local_peer flat breakout (upgrade libvirt agent on this "
            f"hypervisor). Details: {err}"
        )
    return err


async def reconcile_link(
    session: AsyncSession,
    link: NetworkLink,
    *,
    proxy: AgentProxy,
    breakout: BreakoutControllerClient,
    settings: Settings,
    kafka: HuyKafkaProducer | None = None,
) -> NetworkLink:
    if link.status == "deleting":
        return await _reconcile_delete(session, link, proxy=proxy, kafka=kafka)
    if link.link_type == "local":
        return await _reconcile_apply_local(session, link, proxy=proxy, settings=settings, kafka=kafka)
    return await _reconcile_apply(
        session, link, proxy=proxy, breakout=breakout, settings=settings, kafka=kafka
    )


async def _reconcile_apply_local(
    session: AsyncSession,
    link: NetworkLink,
    *,
    proxy: AgentProxy,
    settings: Settings,
    kafka: HuyKafkaProducer | None,
) -> NetworkLink:
    link.status = "applying"
    link.last_error = None
    await session.commit()

    left_cidr = link.left_vnet_cidr or ""
    right_cidr = link.right_vnet_cidr or ""
    if not left_cidr or not right_cidr:
        link.status = "error"
        link.last_error = "Missing vnet CIDR for local link"
        await session.commit()
        await session.refresh(link)
        return link

    try:
        await proxy.put_wireguard_breakout(
            link.left_agent_id,
            link.organization_id,
            link.left_network_name,
            disabled_wireguard(),
        )
        await proxy.put_wireguard_breakout(
            link.right_agent_id,
            link.organization_id,
            link.right_network_name,
            disabled_wireguard(),
        )
        await proxy.put_flat_breakout(
            link.left_agent_id,
            link.organization_id,
            link.left_network_name,
            flat_local_peer(right_cidr),
        )
        await proxy.put_flat_breakout(
            link.right_agent_id,
            link.organization_id,
            link.right_network_name,
            flat_local_peer(left_cidr),
        )

        drift = await _detect_drift_local(link, proxy, left_cidr, right_cidr)
        link.config_drift = drift
        link.status = "connected"
        link.applied_generation = link.desired_generation
        link.last_error = None
    except Exception as exc:
        logger.warning("local_link_reconcile_failed", link_id=link.id, error=str(exc))
        link.status = "error"
        link.last_error = _format_reconcile_error(exc)

    await session.commit()
    await session.refresh(link)
    if kafka is not None:
        try:
            await publish_link_event(kafka, link)
        except Exception as exc:
            logger.warning("link_kafka_publish_failed", link_id=link.id, error=str(exc))
    return link


async def _reconcile_apply(
    session: AsyncSession,
    link: NetworkLink,
    *,
    proxy: AgentProxy,
    breakout: BreakoutControllerClient,
    settings: Settings,
    kafka: HuyKafkaProducer | None,
) -> NetworkLink:
    link.status = "applying"
    link.last_error = None
    await session.commit()

    left_priv = decrypt_private_key(link.left_private_key_enc, settings)
    right_priv = decrypt_private_key(link.right_private_key_enc, settings)

    plan_body = {
        "link_id": link.id,
        "left": {
            "agent_id": link.left_agent_id,
            "network_name": link.left_network_name,
            "vnet_cidr": link.left_vnet_cidr or "",
            "tunnel_ip": link.left_tunnel_address,
            "private_key": left_priv,
            "public_key": link.left_public_key,
        },
        "right": {
            "agent_id": link.right_agent_id,
            "network_name": link.right_network_name,
            "vnet_cidr": link.right_vnet_cidr or "",
            "tunnel_ip": link.right_tunnel_address,
            "private_key": right_priv,
            "public_key": link.right_public_key,
        },
    }

    try:
        plan = await breakout.plan_link(plan_body)
        left_cfg = plan["left"]
        right_cfg = plan["right"]

        await proxy.put_wireguard_breakout(
            link.left_agent_id,
            link.organization_id,
            link.left_network_name,
            left_cfg,
        )
        await proxy.put_wireguard_breakout(
            link.right_agent_id,
            link.organization_id,
            link.right_network_name,
            right_cfg,
        )

        drift = await _detect_drift_wireguard(link, proxy, left_cfg, right_cfg)
        link.config_drift = drift
        link.status = "connected"
        link.applied_generation = link.desired_generation
        link.last_error = None
    except Exception as exc:
        logger.warning("link_reconcile_failed", link_id=link.id, error=str(exc))
        link.status = "error"
        link.last_error = _format_reconcile_error(exc)

    await session.commit()
    await session.refresh(link)
    if kafka is not None:
        try:
            await publish_link_event(kafka, link)
        except Exception as exc:
            logger.warning("link_kafka_publish_failed", link_id=link.id, error=str(exc))
    return link


async def _reconcile_delete(
    session: AsyncSession,
    link: NetworkLink,
    *,
    proxy: AgentProxy,
    kafka: HuyKafkaProducer | None,
) -> NetworkLink:
    try:
        endpoints = (
            (link.left_agent_id, link.left_network_name),
            (link.right_agent_id, link.right_network_name),
        )
        for agent_id, network_name in endpoints:
            await proxy.put_wireguard_breakout(
                agent_id,
                link.organization_id,
                network_name,
                disabled_wireguard(),
            )
            if link.link_type == "local":
                await proxy.put_flat_breakout(
                    agent_id,
                    link.organization_id,
                    network_name,
                    disabled_flat(),
                )
        await session.delete(link)
        await session.commit()
        logger.info("network_link_deleted", link_id=link.id)
        return link
    except Exception as exc:
        link.status = "error"
        link.last_error = f"Delete failed: {exc}"[:2000]
        await session.commit()
        await session.refresh(link)
        if kafka is not None:
            try:
                await publish_link_event(kafka, link)
            except Exception:
                pass
        return link


async def _detect_drift_local(
    link: NetworkLink,
    proxy: AgentProxy,
    left_cidr: str,
    right_cidr: str,
) -> bool:
    try:
        left_bo = await proxy.get_breakout(
            link.left_agent_id, link.organization_id, link.left_network_name
        )
        right_bo = await proxy.get_breakout(
            link.right_agent_id, link.organization_id, link.right_network_name
        )
    except Exception:
        return True
    return not _flat_local_matches(left_bo.get("flat", {}), right_cidr) or not _flat_local_matches(
        right_bo.get("flat", {}), left_cidr
    )


def _flat_local_matches(flat: dict[str, Any], peer_cidr: str) -> bool:
    if not flat.get("enabled") or flat.get("mode") != "local_peer":
        return False
    exempt = set(flat.get("nat_exempt_cidrs", []) + flat.get("remote_hypervisor_cidrs", []))
    return peer_cidr in exempt


async def _detect_drift_wireguard(
    link: NetworkLink,
    proxy: AgentProxy,
    left_expected: dict[str, Any],
    right_expected: dict[str, Any],
) -> bool:
    try:
        left_actual = await proxy.get_breakout(
            link.left_agent_id, link.organization_id, link.left_network_name
        )
        right_actual = await proxy.get_breakout(
            link.right_agent_id, link.organization_id, link.right_network_name
        )
    except Exception:
        return True
    return not _wg_matches(left_actual.get("wireguard", {}), left_expected) or not _wg_matches(
        right_actual.get("wireguard", {}), right_expected
    )


def _wg_matches(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    if not expected.get("enabled"):
        return not actual.get("enabled")
    if actual.get("address") != expected.get("address"):
        return False
    if actual.get("listen_port") != expected.get("listen_port"):
        return False
    exp_peers = {p.get("public_key") for p in expected.get("peers", [])}
    act_peers = {p.get("public_key") for p in actual.get("peers", [])}
    return exp_peers <= act_peers


async def list_links_to_reconcile(session: AsyncSession) -> list[NetworkLink]:
    result = await session.execute(
        select(NetworkLink).where(
            NetworkLink.status.in_(("pending", "error", "deleting"))
            | (NetworkLink.applied_generation < NetworkLink.desired_generation)
        )
    )
    return list(result.scalars().all())