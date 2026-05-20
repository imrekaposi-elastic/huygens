"""Libvirt platform objects excluded from project/inventory operator views."""

LIBVIRT_SYSTEM_NETWORK = "default"


def is_system_network(name: str | None) -> bool:
    return name == LIBVIRT_SYSTEM_NETWORK


def managed_networks(networks: list[dict]) -> list[dict]:
    return [n for n in networks if not is_system_network(n.get("name"))]
