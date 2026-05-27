"""WireGuard key generation (Curve25519, WG clamping)."""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey


def _clamp_private_key(priv: bytearray) -> None:
    priv[0] &= 248
    priv[31] &= 127
    priv[31] |= 64


def generate_keypair() -> tuple[str, str]:
    """Return (private_key_b64, public_key_b64) in WireGuard encoding."""
    private_key = X25519PrivateKey.generate()
    priv_raw = bytearray(
        private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    _clamp_private_key(priv_raw)
    pub_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(priv_raw).decode(), base64.b64encode(pub_raw).decode()


def generate_keypair_from_seed(seed: bytes | None = None) -> tuple[str, str]:
    """Deterministic keypair for tests only."""
    if seed is None:
        return generate_keypair()
    priv = bytearray(seed[:32].ljust(32, b"\x00"))
    _clamp_private_key(priv)
    private_key = X25519PrivateKey.from_private_bytes(bytes(priv))
    pub_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(priv).decode(), base64.b64encode(pub_raw).decode()


def random_seed() -> bytes:
    return os.urandom(32)
