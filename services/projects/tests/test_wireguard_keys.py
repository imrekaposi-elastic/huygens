"""WireGuard key generation tests."""

from __future__ import annotations

import base64

from huy_projects.services.wireguard_keys import generate_keypair, generate_keypair_from_seed


def test_generate_keypair_lengths() -> None:
    priv, pub = generate_keypair()
    assert len(base64.b64decode(priv)) == 32
    assert len(base64.b64decode(pub)) == 32


def test_generate_keypair_from_seed_is_deterministic() -> None:
    priv1, pub1 = generate_keypair_from_seed(b"\xab" * 32)
    priv2, pub2 = generate_keypair_from_seed(b"\xab" * 32)
    assert priv1 == priv2
    assert pub1 == pub2
