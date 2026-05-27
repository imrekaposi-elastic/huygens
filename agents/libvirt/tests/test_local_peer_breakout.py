"""Tests for local_peer flat breakout and iptables peer-forward rules."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from huy_libvirt_agent.api.schemas.network import FlatBreakoutConfig
from huy_libvirt_agent.services.breakout_service import BreakoutService
from huy_libvirt_agent.services.flat_backend import FlatBackend
from huy_libvirt_agent.services.iptables_manager import IptablesManager


def _nft_script_from_mock(run_mock) -> str:
    for call in run_mock.call_args_list:
        script = call.kwargs.get("input")
        if script:
            return script
    raise AssertionError("nft subprocess.run was not called with a script")


def test_flat_backend_local_peer_skips_ip_commands() -> None:
    with patch("huy_libvirt_agent.services.flat_backend.subprocess.run") as run:
        FlatBackend().apply(
            "lab0",
            FlatBreakoutConfig(
                enabled=True,
                mode="local_peer",
                nat_exempt_cidrs=["10.200.0.0/24"],
            ),
        )
    run.assert_not_called()


def test_flat_backend_bridge_uplink_configures_uplink() -> None:
    with patch("huy_libvirt_agent.services.flat_backend.subprocess.run") as run:
        FlatBackend().apply(
            "lab0",
            FlatBreakoutConfig(enabled=True, mode="bridge_uplink", uplink="eth0"),
        )
    assert run.call_count == 2
    first_cmd = run.call_args_list[0][0][0]
    assert first_cmd[:3] == ["ip", "link", "set"]
    assert first_cmd[3] == "eth0"


def test_apply_vnet_rules_persists_peer_forward_spec(tmp_path: Path) -> None:
    vnets_dir = tmp_path / "vnets"
    mgr = IptablesManager(vnets_dir=vnets_dir)
    peer_cidrs = ["10.200.0.0/24"]

    with patch("huy_libvirt_agent.services.iptables_manager.subprocess.run"):
        mgr.apply_vnet_rules(
            "lab0",
            "192.168.50.0/24",
            ["192.168.50.0/24"],
            [],
            peer_forward_cidrs=peer_cidrs,
        )

    state_path = vnets_dir / "lab0" / "iptables.json"
    assert state_path.is_file()
    state = json.loads(state_path.read_text())
    assert state["spec"]["peer_forward"] == peer_cidrs


def test_apply_vnet_rules_drops_peer_equal_to_vnet_cidr(tmp_path: Path) -> None:
    vnets_dir = tmp_path / "vnets"
    mgr = IptablesManager(vnets_dir=vnets_dir)

    with patch("huy_libvirt_agent.services.iptables_manager.subprocess.run"):
        mgr.apply_vnet_rules(
            "lab0",
            "192.168.50.0/24",
            [],
            [],
            peer_forward_cidrs=["192.168.50.0/24", "10.200.0.0/24"],
        )

    state = json.loads((vnets_dir / "lab0" / "iptables.json").read_text())
    assert state["spec"]["peer_forward"] == ["10.200.0.0/24"]


def test_apply_nft_includes_bidirectional_peer_forward_rules() -> None:
    mgr = IptablesManager()
    with patch("huy_libvirt_agent.services.iptables_manager.subprocess.run") as run:
        mgr.apply_vnet_rules(
            "lab0",
            "192.168.50.0/24",
            ["192.168.50.0/24", "10.200.0.0/24"],
            [],
            peer_forward_cidrs=["10.200.0.0/24"],
        )
    script = _nft_script_from_mock(run)
    assert "ip saddr 192.168.50.0/24 ip daddr 10.200.0.0/24 accept" in script
    assert "ip saddr 10.200.0.0/24 ip daddr 192.168.50.0/24 accept" in script


def test_apply_nft_skips_peer_forward_when_peer_matches_exempt_cidr() -> None:
    mgr = IptablesManager()
    with patch("huy_libvirt_agent.services.iptables_manager.subprocess.run") as run:
        mgr.apply_vnet_rules(
            "lab0",
            "192.168.50.0/24",
            ["192.168.50.0/24"],
            [],
            peer_forward_cidrs=["192.168.50.0/24"],
        )
    script = _nft_script_from_mock(run)
    assert "ip daddr 192.168.50.0/24 accept" not in script


def test_breakout_set_flat_local_peer_uses_remote_hypervisor_cidrs(tmp_path: Path) -> None:
    vnets_dir = tmp_path / "vnets"
    iptables = IptablesManager(vnets_dir=vnets_dir)
    svc = BreakoutService(
        vnets_dir=vnets_dir,
        wg_config_dir=tmp_path / "wireguard",
        iptables=iptables,
    )
    config = FlatBreakoutConfig(
        enabled=True,
        mode="local_peer",
        nat_exempt_cidrs=["10.200.0.0/24"],
        remote_hypervisor_cidrs=["10.201.0.0/24"],
    )

    with (
        patch.object(svc._flat, "apply") as flat_apply,
        patch("huy_libvirt_agent.services.iptables_manager.subprocess.run"),
    ):
        svc.set_flat("lab0", config, "192.168.50.0/24")

    flat_apply.assert_called_once_with("lab0", config)
    state = json.loads((vnets_dir / "lab0" / "iptables.json").read_text())
    assert state["spec"]["peer_forward"] == ["10.201.0.0/24"]
    breakout = json.loads((vnets_dir / "lab0" / "breakout.json").read_text())
    assert breakout["flat"]["mode"] == "local_peer"


def test_breakout_set_flat_local_peer_falls_back_to_nat_exempt_cidrs(tmp_path: Path) -> None:
    vnets_dir = tmp_path / "vnets"
    iptables = IptablesManager(vnets_dir=vnets_dir)
    svc = BreakoutService(
        vnets_dir=vnets_dir,
        wg_config_dir=tmp_path / "wireguard",
        iptables=iptables,
    )
    config = FlatBreakoutConfig(
        enabled=True,
        mode="local_peer",
        nat_exempt_cidrs=["10.200.0.0/24"],
        remote_hypervisor_cidrs=[],
    )

    with (
        patch.object(svc._flat, "apply"),
        patch("huy_libvirt_agent.services.iptables_manager.subprocess.run"),
    ):
        svc.set_flat("lab0", config, "192.168.50.0/24")

    state = json.loads((vnets_dir / "lab0" / "iptables.json").read_text())
    assert state["spec"]["peer_forward"] == ["10.200.0.0/24"]
