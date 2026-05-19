"""RFC1918 pool math and subnet allocation."""

from __future__ import annotations

import ipaddress
import math
from typing import Iterable

RFC1918_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)


class IpamError(ValueError):
    """Invalid pool or allocation request."""


def is_rfc1918(network: ipaddress.IPv4Network) -> bool:
    return any(network.subnet_of(r) for r in RFC1918_NETWORKS)


def parse_network(cidr: str) -> ipaddress.IPv4Network:
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except ValueError as exc:
        raise IpamError(f"Invalid CIDR: {cidr}") from exc
    if net.version != 4:
        raise IpamError("Only IPv4 pools are supported")
    return net


def validate_pool_cidr(cidr: str) -> ipaddress.IPv4Network:
    net = parse_network(cidr)
    if not is_rfc1918(net):
        raise IpamError("Pool must be within RFC1918 private address space")
    if net.prefixlen < 8 or net.prefixlen > 24:
        raise IpamError("Pool prefix length must be between /8 and /24")
    return net


def hosts_to_prefixlen(hosts: int) -> int:
    if hosts < 1:
        raise IpamError("hosts must be at least 1")
    # network + broadcast + hosts
    need = hosts + 2
    host_bits = max(2, math.ceil(math.log2(need)))
    return 32 - host_bits


def _overlaps(candidate: ipaddress.IPv4Network, occupied: Iterable[ipaddress.IPv4Network]) -> bool:
    for other in occupied:
        if candidate.overlaps(other):
            return True
    return False


def next_subnet(
    pool: ipaddress.IPv4Network,
    prefixlen: int,
    occupied: Iterable[str],
    *,
    exceptions: Iterable[str] | None = None,
) -> ipaddress.IPv4Network:
    if prefixlen < pool.prefixlen:
        raise IpamError(f"Requested /{prefixlen} is larger than pool /{pool.prefixlen}")
    used = [parse_network(c) for c in occupied]
    reserved = [parse_network(c) for c in (exceptions or [])]
    all_blocked = used + reserved
    for subnet in pool.subnets(new_prefix=prefixlen):
        if not _overlaps(subnet, all_blocked):
            return subnet
    raise IpamError("No free subnet of requested size in pool")


def plan_subnets(
    pool_cidr: str,
    *,
    network_count: int,
    hosts_per_network: int,
    occupied: Iterable[str] = (),
    exceptions: Iterable[str] | None = None,
) -> list[str]:
    if network_count < 1:
        raise IpamError("network_count must be at least 1")
    pool = validate_pool_cidr(pool_cidr)
    prefixlen = hosts_to_prefixlen(hosts_per_network)
    planned: list[str] = []
    blocked = list(occupied) + list(exceptions or [])
    for _ in range(network_count):
        subnet = next_subnet(pool, prefixlen, planned + blocked, exceptions=exceptions)
        planned.append(str(subnet))
    return planned
