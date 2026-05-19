"""System network flag tests."""

from __future__ import annotations

from huy_libvirt_agent.services.system_networks import network_access_flags


def test_default_network_is_readonly() -> None:
    readonly, deletable = network_access_flags("default", agent_managed=False)
    assert readonly is True
    assert deletable is False


def test_managed_lab_network_is_deletable() -> None:
    readonly, deletable = network_access_flags("lab0", agent_managed=True)
    assert readonly is False
    assert deletable is True


def test_unmanaged_libvirt_network_is_readonly() -> None:
    readonly, deletable = network_access_flags("virbr1", agent_managed=False)
    assert readonly is True
    assert deletable is False
