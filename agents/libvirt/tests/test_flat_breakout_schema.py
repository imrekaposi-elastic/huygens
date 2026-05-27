"""Flat breakout config validation."""

import pytest
from pydantic import ValidationError

from huy_libvirt_agent.api.schemas.network import FlatBreakoutConfig


def test_flat_requires_uplink_when_enabled() -> None:
    with pytest.raises(ValidationError, match="uplink"):
        FlatBreakoutConfig(enabled=True, mode="bridge_uplink", uplink="")


def test_flat_rejects_invalid_uplink() -> None:
    with pytest.raises(ValidationError, match="uplink"):
        FlatBreakoutConfig(enabled=True, mode="macvlan", uplink="../eth0")


def test_flat_local_peer_without_uplink_ok() -> None:
    cfg = FlatBreakoutConfig(enabled=True, mode="local_peer", uplink="")
    assert cfg.mode == "local_peer"
