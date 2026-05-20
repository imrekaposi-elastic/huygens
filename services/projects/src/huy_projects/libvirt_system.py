"""Libvirt platform objects excluded from project operator views."""

LIBVIRT_SYSTEM_NETWORK = "default"


def is_system_network(name: str | None) -> bool:
    return name == LIBVIRT_SYSTEM_NETWORK
