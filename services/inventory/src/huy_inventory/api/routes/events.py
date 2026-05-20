"""Inventory live events (SSE) — Authorization header only."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from huy_auth.auth_context import AuthContext
from huy_inventory.api.deps import CurrentUserDep, InventoryReadDep, reject_query_token_auth
from huy_inventory.services.sse_hub import get_event_hub
from huy_inventory.services.sse_kafka import user_may_receive_event

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory-events"])


async def _sse_generator(user: AuthContext) -> AsyncIterator[str]:
    hub = get_event_hub()
    queue = await hub.subscribe()
    try:
        yield ": connected\n\n"
        while True:
            try:
                line = await asyncio.wait_for(queue.get(), timeout=30.0)
            except TimeoutError:
                yield ": keepalive\n\n"
                continue
            try:
                envelope = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not user_may_receive_event(user, envelope):
                continue
            event_type = envelope.get("type", "inventory.snapshot")
            yield f"event: {event_type}\ndata: {line}\n\n"
    finally:
        await hub.unsubscribe(queue)


@router.get(
    "/events/stream",
    response_class=StreamingResponse,
    dependencies=[Depends(reject_query_token_auth)],
)
async def inventory_events_stream(
    _read: InventoryReadDep,
    user: CurrentUserDep,
) -> StreamingResponse:
    """
    Server-Sent Events for inventory snapshots.

    **Auth:** `Authorization: Bearer` only. Query-string tokens (`?token=`) return 400.
    **Client:** use fetch-based SSE (`@microsoft/fetch-event-source`), not `EventSource`.
    """
    return StreamingResponse(
        _sse_generator(user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
