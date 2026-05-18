"""OpenAPI server URL helpers."""

from __future__ import annotations

from huy_libvirt_agent.config import Settings
from huy_libvirt_agent.openapi_servers import openapi_servers


def _settings(**kwargs) -> Settings:
    base = {
        "agent_token": "t",
        "agent_country": "NL",
        "agent_city": "A",
        "agent_company": "C",
    }
    base.update(kwargs)
    return Settings(**base)


def test_relative_server_when_bind_all_interfaces() -> None:
    s = _settings(bind_host="0.0.0.0", tls_enabled=True)
    assert openapi_servers(s) == [
        {"url": "/", "description": "Same host as this page (recommended for Swagger)"}
    ]


def test_public_base_url_overrides_bind() -> None:
    s = _settings(
        bind_host="0.0.0.0",
        public_base_url="https://dommel.kaposi.net:8765",
    )
    assert openapi_servers(s)[0]["url"] == "https://dommel.kaposi.net:8765"
