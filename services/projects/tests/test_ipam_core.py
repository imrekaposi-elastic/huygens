"""IPAM core unit tests."""

from __future__ import annotations

import pytest

from huy_projects.ipam.core import IpamError, hosts_to_prefixlen, plan_subnets, validate_pool_cidr


def test_validate_rfc1918_pool() -> None:
    net = validate_pool_cidr("10.100.0.0/16")
    assert str(net) == "10.100.0.0/16"


def test_reject_public_pool() -> None:
    with pytest.raises(IpamError, match="RFC1918"):
        validate_pool_cidr("8.8.8.0/24")


def test_hosts_to_prefixlen() -> None:
    assert hosts_to_prefixlen(30) == 27
    assert hosts_to_prefixlen(250) == 24


def test_plan_subnets_respects_exceptions() -> None:
    planned = plan_subnets(
        "10.200.0.0/22",
        network_count=2,
        hosts_per_network=10,
        exceptions=["10.200.0.0/28"],
    )
    assert len(planned) == 2
    assert "10.200.0.0/28" not in planned
