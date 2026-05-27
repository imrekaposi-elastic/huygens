"""Flat L2 breakout via bridge uplink."""

from __future__ import annotations

import subprocess

import structlog

from huy_libvirt_agent.api.schemas.network import FlatBreakoutConfig

logger = structlog.get_logger(__name__)


class FlatBackend:
    def apply(self, vnet: str, config: FlatBreakoutConfig) -> None:
        if config.mode == "local_peer":
            logger.info("flat_breakout_local_peer", vnet=vnet, peers=config.nat_exempt_cidrs)
            return
        bridge = f"br-{vnet}"
        if config.mode == "bridge_uplink":
            subprocess.run(
                ["ip", "link", "set", config.uplink, "up"],
                capture_output=True,
                check=False,
            )
            subprocess.run(
                ["ip", "link", "set", config.uplink, "master", bridge],
                capture_output=True,
                check=False,
            )
            logger.info("flat_breakout_bridge_uplink", vnet=vnet, uplink=config.uplink)
        elif config.mode == "macvlan":
            subprocess.run(
                [
                    "ip",
                    "link",
                    "add",
                    f"mv-{vnet}",
                    "link",
                    config.uplink,
                    "type",
                    "macvlan",
                    "mode",
                    "bridge",
                ],
                capture_output=True,
                check=False,
            )
            logger.info("flat_breakout_macvlan", vnet=vnet, uplink=config.uplink)
