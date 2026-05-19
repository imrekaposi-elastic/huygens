"""Agent bearer token generation, hashing, and encryption for the registry vault."""

from __future__ import annotations

import base64
import hashlib
import secrets

import bcrypt
from cryptography.fernet import Fernet, InvalidToken


def generate_agent_token() -> str:
    return secrets.token_urlsafe(32)


def hash_agent_token(token: str) -> str:
    return bcrypt.hashpw(token.encode(), bcrypt.gensalt()).decode()


def verify_agent_token(token: str, token_hash: str) -> bool:
    try:
        return bcrypt.checkpw(token.encode(), token_hash.encode())
    except ValueError:
        return False


def _fernet(key: str) -> Fernet:
    digest = hashlib.sha256(key.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(digest)
    return Fernet(fernet_key)


def encrypt_agent_token(token: str, encryption_key: str) -> str:
    return _fernet(encryption_key).encrypt(token.encode()).decode()


def decrypt_agent_token(ciphertext: str, encryption_key: str) -> str:
    try:
        return _fernet(encryption_key).decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Invalid agent token ciphertext") from exc
