"""Scoped nftables/iptables chain management."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class IptablesManager:
    def __init__(self, backend: str = "nft", vnets_dir: Path | None = None) -> None:
        self._backend = backend
        self._vnets_dir = vnets_dir

    def chain_names(self, vnet: str) -> dict[str, str]:
        safe = vnet.replace("-", "_")
        return {
            "fwd": f"HUY-FWD-{safe}",
            "nat_pre": f"HUY-NAT-PRE-{safe}",
            "nat_post": f"HUY-NAT-POST-{safe}",
        }

    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def apply_vnet_rules(
        self,
        vnet: str,
        vnet_cidr: str,
        nat_exempt_cidrs: list[str],
        dnat_rules: list[dict],
        snat_interface: str | None = None,
    ) -> str:
        chains = self.chain_names(vnet)
        exempt = list({vnet_cidr, *nat_exempt_cidrs})
        spec = {
            "vnet": vnet,
            "chains": chains,
            "exempt": exempt,
            "dnat": dnat_rules,
            "snat_interface": snat_interface,
        }
        checksum = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
        if self._vnets_dir:
            state_path = self._vnets_dir / vnet / "iptables.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps({"spec": spec, "checksum": checksum}, indent=2))
        self._apply_nft(chains, exempt, dnat_rules, snat_interface)
        logger.info("iptables_applied", vnet=vnet, checksum=checksum[:12])
        return checksum

    def _apply_nft(self, chains: dict, exempt: list[str], dnat_rules: list, snat_if: str | None) -> None:
        lines = [
            "flush table ip huy",
            "table ip huy {",
        ]
        for hook, name in [("prerouting", chains["nat_pre"]), ("postrouting", chains["nat_post"])]:
            lines.append(f"  chain {name} {{ type nat hook {hook} priority 0; policy accept; }}")
        lines.append(f"  chain {chains['fwd']} {{ type filter hook forward priority 0; policy accept; }}")
        for rule in dnat_rules:
            proto = rule.get("protocol", "tcp")
            if proto == "both":
                for p in ("tcp", "udp"):
                    lines.append(
                        f"  add rule ip huy {chains['nat_pre']} "
                        f"{p} dport {rule['public_port']} dnat to {rule['guest_ip']}:{rule['guest_port']}"
                    )
            else:
                lines.append(
                    f"  add rule ip huy {chains['nat_pre']} "
                    f"{proto} dport {rule['public_port']} dnat to {rule['guest_ip']}:{rule['guest_port']}"
                )
        for cidr in exempt:
            lines.append(
                f"  add rule ip huy {chains['nat_post']} ip daddr {cidr} return"
            )
        if snat_if:
            lines.append(
                f"  add rule ip huy {chains['nat_post']} oifname \"{snat_if}\" masquerade"
            )
        lines.append("}")
        script = "\n".join(lines)
        proc = self._run(["nft", "-f", "-"])
        if proc.returncode != 0 and hasattr(proc, "stdin"):
            pass
        try:
            subprocess.run(["nft", "-f", "-"], input=script, text=True, capture_output=True, check=False)
        except FileNotFoundError:
            logger.warning("nft_not_available", backend=self._backend)

    def checksum_for_vnet(self, vnet: str) -> str | None:
        if not self._vnets_dir:
            return None
        path = self._vnets_dir / vnet / "iptables.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return data.get("checksum")
