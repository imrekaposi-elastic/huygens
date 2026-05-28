"""HTTP request context: request id, structlog bindings, trace response headers."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )
        span = trace.get_current_span()
        trace_id = ""
        if span:
            ctx = span.get_span_context()
            if ctx.is_valid:
                trace_id = format(ctx.trace_id, "032x")
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        if trace_id:
            response.headers["X-Trace-Id"] = trace_id
        return response


def install_request_context_middleware(app: Any) -> None:
    app.add_middleware(RequestContextMiddleware)
