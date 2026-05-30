"""WebSocket SSH relay (Phase 9)."""

from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def relay_client(tmp_data_dir) -> TestClient:
    from huy_libvirt_agent.app_state import AppState
    from huy_libvirt_agent.config import get_settings
    from huy_libvirt_agent.main import create_app

    os.environ["SSH_GATEWAY_SERVICE_TOKEN"] = "relay-secret"
    os.environ["HUY_AGENT_ID"] = "agent-123"
    get_settings.cache_clear()
    state = AppState.from_settings(get_settings())
    app = create_app(state)
    with TestClient(app) as c:
        yield c


def test_ssh_relay_ws_handshake_without_token(relay_client: TestClient) -> None:
    with relay_client.websocket_connect("/api/v1/ssh/relay/ws") as ws:
        ws.send_text("{}")
        assert ws.receive_text().startswith("ERR")


def test_ssh_relay_ws_rejects_bad_token(relay_client: TestClient) -> None:
    payload = {
        "session_token": "bad.token",
        "guest_ip": "10.0.0.1",
        "guest_port": 22,
        "linux_user": "ubuntu",
        "session_id": "sess-1",
    }
    with relay_client.websocket_connect("/api/v1/ssh/relay/ws") as ws:
        ws.send_text(json.dumps(payload))
        assert ws.receive_text() == "ERR unauthorized\n"
