"""Append-only request audit middleware."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from huy_libvirt_agent.app_state import AppState


def _parse_resource(path: str) -> tuple[str | None, str | None]:
    parts = path.strip("/").split("/")
    resource_type = None
    resource_id = None
    if len(parts) >= 3 and parts[0] == "api":
        resource_type = parts[2]
        if len(parts) > 3 and parts[3] not in ("breakout", "dnat"):
            resource_id = parts[3]
    return resource_type, resource_id


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        state: AppState = request.app.state.app_state
        if (
            not state.audit_store
            or request.url.path in ("/healthz", "/readyz", "/metrics")
            or request.url.path.startswith("/api/v1/ssh/")
            or request.headers.get("upgrade", "").lower() == "websocket"
        ):
            return await call_next(request)

        start = time.perf_counter()
        body = await request.body()

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive  # noqa: SLF001

        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)
        resource_type, resource_id = _parse_resource(request.url.path)
        action_map = {
            "GET": "read",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
        }
        action = action_map.get(request.method, "unknown")
        actor = request.headers.get("X-Actor") or "anonymous"
        body_hash = hashlib.sha256(body).hexdigest() if body else None
        span_ctx = getattr(request.state, "request_id", "")
        record = {
            "request_id": span_ctx,
            "trace_id": response.headers.get("X-Trace-Id", ""),
            "actor": actor,
            "auth_method": "bearer",
            "method": request.method,
            "path": request.url.path,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "request_body_sha256": body_hash,
            "response_status": response.status_code,
            "outcome": "success" if response.status_code < 400 else "failure",
            "duration_ms": duration_ms,
            "client_ip": request.client.host if request.client else None,
            "agent_labels": state.settings.agent_labels,
            "resource_labels": state.settings.agent_labels,
        }
        state.audit_store.write(record)
        return response
