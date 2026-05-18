"""Agent endpoint tests."""

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_agent_requires_auth(client: TestClient) -> None:
    r = client.get("/api/v1/agent")
    assert r.status_code == 401


def test_agent_settings(client: TestClient, auth_headers: dict) -> None:
    r = client.get("/api/v1/agent", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["settings"]["country"] == "NL"
    assert data["settings"]["city"] == "Amsterdam"
    assert data["settings"]["company"] == "Huygens Test"
    assert data["tls"]["enabled"] is False
    assert data["tls"]["scheme"] == "http"
