"""Agent URL validation tests."""

from __future__ import annotations

import pytest

from huy_auth.url_safety import AgentUrlError, validate_agent_base_url


def test_accepts_https_origin() -> None:
    assert validate_agent_base_url("https://agent.example:8765/") == "https://agent.example:8765"


def test_rejects_credentials() -> None:
    with pytest.raises(AgentUrlError, match="credentials"):
        validate_agent_base_url("https://user:pass@agent.example")


def test_rejects_path() -> None:
    with pytest.raises(AgentUrlError, match="path"):
        validate_agent_base_url("https://agent.example/api/v1")
