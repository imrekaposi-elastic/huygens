"""Multi-token authentication tests."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from huy_libvirt_agent.config import Settings


def test_valid_agent_tokens_parses_primary_and_extra() -> None:
    s = Settings(
        agent_token="one,two",
        agent_tokens_extra="three",
        agent_country="NL",
        agent_city="A",
        agent_company="C",
    )
    assert s.valid_agent_tokens == frozenset({"one", "two", "three"})


def test_any_configured_token_authenticates(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from huy_libvirt_agent.config import get_settings

    monkeypatch.setenv("HUY_AGENT_TOKEN", "primary")
    monkeypatch.setenv("HUY_AGENT_TOKENS", "secondary,tertiary")
    get_settings.cache_clear()
    state = client.app.state.app_state
    state.settings = get_settings()

    for token in ("primary", "secondary", "tertiary"):
        r = client.get("/api/v1/agent", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, token

    r = client.get("/api/v1/agent", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401

    get_settings.cache_clear()
    os.environ.pop("HUY_AGENT_TOKENS", None)
