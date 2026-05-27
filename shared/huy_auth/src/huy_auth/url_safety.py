"""Validate agent base URLs before outbound HTTP (CodeQL SSRF guard)."""

from __future__ import annotations

from urllib.parse import urlparse

_BLOCKED_SCHEMES = frozenset({"file", "gopher", "ftp", "data", "javascript"})


class AgentUrlError(ValueError):
    """Raised when an agent base URL is not allowed."""


def validate_agent_base_url(url: str) -> str:
    """
    Normalize and validate a libvirt agent base URL stored in the registry.

    Rejects non-http(s) schemes, embedded credentials, and path/query fragments so
    downstream clients only request fixed API paths under the registered origin.
    """
    raw = url.strip()
    if not raw:
        raise AgentUrlError("Agent base URL is required")
    parsed = urlparse(raw)
    if parsed.scheme in _BLOCKED_SCHEMES or parsed.scheme not in {"https", "http"}:
        raise AgentUrlError("Agent base URL must use http or https")
    if parsed.username or parsed.password:
        raise AgentUrlError("Agent base URL must not include credentials")
    host = parsed.hostname
    if not host:
        raise AgentUrlError("Agent base URL must include a hostname")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise AgentUrlError("Agent base URL must not include a path, query, or fragment")
    port = parsed.port
    if port is not None and not (1 <= port <= 65535):
        raise AgentUrlError("Agent base URL port is out of range")
    netloc = host if port is None else f"{host}:{port}"
    return f"{parsed.scheme}://{netloc}".rstrip("/")
