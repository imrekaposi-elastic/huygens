"""Org SSH CA generation and secure storage."""

from __future__ import annotations

import base64
import hashlib
import subprocess
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from huy_iam.config import Settings
from huy_iam.models import SshOrgCa


def _fernet(settings: Settings) -> Fernet:
    digest = hashlib.sha256(settings.ssh_ca_encryption_key.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def _generate_ca_keypair() -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "huy-ca"
        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-f", str(base), "-N", "", "-C", "huy-ssh-ca"],
            check=True,
            capture_output=True,
        )
        public_openssh = base.with_suffix(".pub").read_text().strip()
        private_openssh = base.read_text()
    return public_openssh, private_openssh


async def ensure_org_ca(session: AsyncSession, settings: Settings, organization_id: str) -> SshOrgCa:
    row = await session.get(SshOrgCa, organization_id)
    if row is not None:
        return row
    public_openssh, private_openssh = _generate_ca_keypair()
    encrypted = _fernet(settings).encrypt(private_openssh.encode()).decode()
    row = SshOrgCa(
        organization_id=organization_id,
        public_key_openssh=public_openssh.strip(),
        private_key_encrypted=encrypted,
    )
    session.add(row)
    await session.flush()
    return row


async def get_org_ca(session: AsyncSession, organization_id: str) -> SshOrgCa | None:
    return await session.get(SshOrgCa, organization_id)


async def get_org_ca_public_key(session: AsyncSession, organization_id: str) -> str | None:
    row = await get_org_ca(session, organization_id)
    return row.public_key_openssh if row else None


def decrypt_ca_private_key(settings: Settings, row: SshOrgCa) -> str:
    return _fernet(settings).decrypt(row.private_key_encrypted.encode()).decode()


async def list_org_cas(session: AsyncSession) -> list[SshOrgCa]:
    result = await session.scalars(select(SshOrgCa))
    return list(result.all())
