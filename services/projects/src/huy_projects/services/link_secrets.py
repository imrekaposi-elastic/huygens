"""Encrypt WireGuard private keys at rest (same Fernet vault as registry agent tokens)."""

from __future__ import annotations

from huy_auth.agent_tokens import decrypt_agent_token, encrypt_agent_token

from huy_projects.config import Settings


def encrypt_private_key(private_key: str, settings: Settings) -> str:
    return encrypt_agent_token(private_key, settings.agent_token_encryption_key)


def decrypt_private_key(ciphertext: str, settings: Settings) -> str:
    return decrypt_agent_token(ciphertext, settings.agent_token_encryption_key)
