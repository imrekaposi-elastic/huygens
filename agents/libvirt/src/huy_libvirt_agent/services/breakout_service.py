"""WireGuard and flat L2 breakout orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import structlog

from huy_libvirt_agent.api.schemas.network import FlatBreakoutConfig, WireGuardBreakoutConfig
from huy_libvirt_agent.services.flat_backend import FlatBackend
from huy_libvirt_agent.services.iptables_manager import IptablesManager
from huy_libvirt_agent.services.path_safety import PathSafetyError, safe_child_dir, safe_registry_name
from huy_libvirt_agent.services.wireguard_backend import WireGuardBackend

logger = structlog.get_logger(__name__)


class BreakoutService:
    def __init__(
        self,
        vnets_dir: Path,
        wg_config_dir: Path,
        iptables: IptablesManager,
    ) -> None:
        self._vnets_dir = vnets_dir
        self._wg = WireGuardBackend(wg_config_dir)
        self._flat = FlatBackend()
        self._iptables = iptables

    def _vnet_path(self, name: str) -> Path:
        try:
            p = safe_child_dir(self._vnets_dir, name)
        except PathSafetyError as exc:
            raise ValueError(str(exc)) from exc
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_breakout(self, vnet: str) -> dict:
        path = self._vnet_path(vnet) / "breakout.json"
        if path.exists():
            return json.loads(path.read_text())
        return {
            "wireguard": WireGuardBreakoutConfig().model_dump(),
            "flat": FlatBreakoutConfig(enabled=False, uplink="").model_dump(),
        }

    def set_wireguard(self, vnet: str, config: WireGuardBreakoutConfig, vnet_cidr: str) -> None:
        data = self.get_breakout(vnet)
        data["wireguard"] = config.model_dump()
        self._save_breakout(vnet, data)
        if config.enabled:
            self._wg.apply(vnet, config)
        self._reconcile_iptables(vnet, vnet_cidr, data)

    def set_flat(self, vnet: str, config: FlatBreakoutConfig, vnet_cidr: str) -> None:
        data = self.get_breakout(vnet)
        data["flat"] = config.model_dump()
        self._save_breakout(vnet, data)
        if config.enabled:
            self._flat.apply(vnet, config)
        self._reconcile_iptables(vnet, vnet_cidr, data)

    def _save_breakout(self, vnet: str, data: dict) -> None:
        (self._vnet_path(vnet) / "breakout.json").write_text(json.dumps(data, indent=2))

    def _reconcile_iptables(self, vnet: str, vnet_cidr: str, breakout: dict) -> None:
        exempt: list[str] = [vnet_cidr]
        wg = breakout.get("wireguard", {})
        flat = breakout.get("flat", {})
        peer_forward: list[str] = []
        if wg.get("enabled"):
            exempt.extend(wg.get("nat_exempt_cidrs", []))
        if flat.get("enabled"):
            exempt.extend(flat.get("nat_exempt_cidrs", flat.get("remote_hypervisor_cidrs", [])))
            if flat.get("mode") == "local_peer":
                peer_forward = list(
                    flat.get("remote_hypervisor_cidrs", []) or flat.get("nat_exempt_cidrs", [])
                )
        dnat_path = self._vnet_path(vnet) / "dnat.json"
        dnat_rules = json.loads(dnat_path.read_text()) if dnat_path.exists() else []
        self._iptables.apply_vnet_rules(
            vnet, vnet_cidr, exempt, dnat_rules, peer_forward_cidrs=peer_forward
        )
