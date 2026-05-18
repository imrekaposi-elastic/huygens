"""OpenAPI server URLs for Swagger / ReDoc."""

from __future__ import annotations

from huy_libvirt_agent.config import Settings

_ALL_INTERFACES = frozenset({"0.0.0.0", "::", "[::]", ""})


def openapi_servers(settings: Settings) -> list[dict[str, str]]:
    """Build OpenAPI servers list so Swagger calls the same host as /docs."""
    if settings.public_base_url:
        return [
            {
                "url": settings.public_base_url.rstrip("/"),
                "description": "Public API base URL",
            }
        ]
    if settings.bind_host in _ALL_INTERFACES or settings.bind_uds:
        return [
            {
                "url": "/",
                "description": "Same host as this page (recommended for Swagger)",
            }
        ]
    scheme = "https" if settings.tls_enabled else "http"
    return [
        {
            "url": f"{scheme}://{settings.bind_host}:{settings.bind_port}",
            "description": "Configured bind address",
        }
    ]
