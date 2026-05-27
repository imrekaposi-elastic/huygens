"""WireGuard configuration via wg-quick."""

from __future__ import annotations

import subprocess
from pathlib import Path

import structlog

from huy_libvirt_agent.api.schemas.network import WireGuardBreakoutConfig
from huy_libvirt_agent.services.path_safety import PathSafetyError, safe_registry_name

logger = structlog.get_logger(__name__)


class WireGuardBackend:
    def __init__(self, config_dir: Path) -> None:
        self._config_dir = config_dir

    def _ensure_config_dir(self) -> None:
        self._config_dir.mkdir(parents=True, exist_ok=True)

    def apply(self, vnet: str, config: WireGuardBreakoutConfig) -> None:
        self._ensure_config_dir()
        try:
            safe_vnet = safe_registry_name(vnet)
        except PathSafetyError as exc:
            raise ValueError(str(exc)) from exc
        iface = config.interface or f"wg-{safe_vnet}"
        conf_path = self._config_dir / f"huy-{safe_vnet}.conf"
        lines = [
            "[Interface]",
            f"PrivateKey = {config.private_key}",
            f"Address = {config.address}",
            f"ListenPort = {config.listen_port}",
        ]
        for route in config.vnet_routes:
            lines.append(f"PostUp = ip route add {route} dev %i")
            lines.append(f"PostDown = ip route del {route} dev %i")
        for peer in config.peers:
            lines.extend(
                [
                    "",
                    "[Peer]",
                    f"PublicKey = {peer.public_key}",
                    f"AllowedIPs = {','.join(peer.allowed_ips)}",
                ]
            )
            if peer.endpoint:
                lines.append(f"Endpoint = {peer.endpoint}")
        conf_path.write_text("\n".join(lines) + "\n")
        subprocess.run(["wg-quick", "up", str(conf_path)], capture_output=True, check=False)
        logger.info("wireguard_applied", vnet=vnet, interface=iface)
