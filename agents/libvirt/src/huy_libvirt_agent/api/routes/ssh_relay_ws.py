"""WebSocket SSH relay on the agent HTTPS port (for remote ssh-gateway)."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from huy_libvirt_agent.api.deps import StateDep
from huy_libvirt_agent.services.ssh_relay import RelayRequest, verify_session_token

router = APIRouter(prefix="/api/v1/ssh", tags=["ssh"])


async def _bridge_ws_to_tcp(
    websocket: WebSocket,
    guest_ip: str,
    guest_port: int,
) -> None:
    guest_reader, guest_writer = await asyncio.open_connection(guest_ip, guest_port)
    await websocket.send_text("OK")

    async def ws_to_guest() -> None:
        try:
            while True:
                msg = await websocket.receive()
                if msg["type"] == "websocket.disconnect":
                    break
                data = msg.get("bytes") or msg.get("text", "").encode()
                if data:
                    guest_writer.write(data)
                    await guest_writer.drain()
        finally:
            guest_writer.close()
            await guest_writer.wait_closed()

    async def guest_to_ws() -> None:
        try:
            while True:
                data = await guest_reader.read(32 * 1024)
                if not data:
                    break
                await websocket.send_bytes(data)
        except WebSocketDisconnect:
            pass

    await asyncio.gather(ws_to_guest(), guest_to_ws())


@router.websocket("/relay/ws")
async def ssh_relay_websocket(websocket: WebSocket, state: StateDep) -> None:
    """Bidirectional relay to guest :22 after session-token validation."""
    await websocket.accept()
    secret = state.settings.ssh_gateway_service_token
    agent_id = state.settings.agent_id
    if not secret:
        await websocket.send_text("ERR relay disabled\n")
        await websocket.close()
        return
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
        payload = json.loads(raw)
        req = RelayRequest(
            session_token=payload.get("session_token", ""),
            guest_ip=payload.get("guest_ip", ""),
            guest_port=int(payload.get("guest_port", 22)),
            linux_user=payload.get("linux_user", ""),
            session_id=payload.get("session_id", ""),
        )
        if not verify_session_token(secret, req.session_id, agent_id, req.session_token):
            await websocket.send_text("ERR unauthorized\n")
            await websocket.close()
            return
        if not req.guest_ip:
            await websocket.send_text("ERR missing guest_ip\n")
            await websocket.close()
            return
        await _bridge_ws_to_tcp(websocket, req.guest_ip, req.guest_port)
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        await websocket.send_text(f"ERR {exc}\n")
        await websocket.close()
