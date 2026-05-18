"""CloudEvents-style domain event models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    type: str
    time: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    datacontenttype: str = "application/json"
    correlation_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    def to_cloud_event(self) -> dict[str, Any]:
        return self.model_dump()
