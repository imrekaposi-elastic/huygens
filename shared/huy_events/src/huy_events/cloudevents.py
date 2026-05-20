"""CloudEvents 1.0 envelope builder."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any


def build_envelope(
    *,
    event_type: str,
    source: str,
    data: dict[str, Any],
    subject: str | None = None,
    event_id: str | None = None,
    time: datetime | str | None = None,
    dataschema: str | None = None,
) -> dict[str, Any]:
    if isinstance(time, datetime):
        time_str = time.astimezone(UTC).isoformat()
    elif isinstance(time, str):
        time_str = time
    else:
        time_str = datetime.now(UTC).isoformat()

    envelope: dict[str, Any] = {
        "specversion": "1.0",
        "id": event_id or str(uuid.uuid4()),
        "type": event_type,
        "source": source,
        "time": time_str,
        "datacontenttype": "application/json",
        "data": data,
    }
    if subject is not None:
        envelope["subject"] = subject
    if dataschema is not None:
        envelope["dataschema"] = dataschema
    return envelope
