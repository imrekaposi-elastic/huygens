"""Validate ssh-gateway session tokens and TCP relay to guest SSH."""

from __future__ import annotations

import asyncio
import hmac
import hashlib
import json
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class RelayRequest:
    session_token: str
    guest_ip: str
    guest_port: int
    linux_user: str
    session_id: str


def verify_session_token(secret: str, session_id: str, agent_id: str, token: str) -> bool:
    if not secret or "." not in token:
        return False
    mac_hex, exp_str = token.rsplit(".", 1)
    payload = f"{session_id}|{agent_id}|{exp_str}"
    expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac_hex, expected)


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, label: str) -> None:
    try:
        while True:
            data = await reader.read(32 * 1024)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception as exc:  # noqa: BLE001
        logger.debug("ssh_relay_pipe_closed", label=label, error=str(exc))
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    *,
    secret: str,
    agent_id: str,
) -> None:
    peer = writer.get_extra_info("peername")
    try:
        line = await asyncio.wait_for(reader.readline(), timeout=10.0)
        payload = json.loads(line.decode().strip())
        req = RelayRequest(
            session_token=payload.get("session_token", ""),
            guest_ip=payload.get("guest_ip", ""),
            guest_port=int(payload.get("guest_port", 22)),
            linux_user=payload.get("linux_user", ""),
            session_id=payload.get("session_id", ""),
        )
        if not verify_session_token(secret, req.session_id, agent_id, req.session_token):
            writer.write(b"ERR unauthorized\n")
            await writer.drain()
            return
        if not req.guest_ip:
            writer.write(b"ERR missing guest_ip\n")
            await writer.drain()
            return
        guest_reader, guest_writer = await asyncio.open_connection(req.guest_ip, req.guest_port)
        writer.write(b"OK\n")
        await writer.drain()
        await asyncio.gather(
            _pipe(reader, guest_writer, "client_to_guest"),
            _pipe(guest_reader, writer, "guest_to_client"),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("ssh_relay_session_failed", peer=peer, error=str(exc))
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass


async def start_relay_server(
    *,
    host: str,
    port: int,
    secret: str,
    agent_id: str,
) -> asyncio.Server:
    async def _handler(r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
        await handle_client(r, w, secret=secret, agent_id=agent_id)

    server = await asyncio.start_server(_handler, host, port)
    logger.info("ssh_relay_listening", host=host, port=port)
    return server
