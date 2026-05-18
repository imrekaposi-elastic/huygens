"""Shared API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from huy_libvirt_agent.api.schemas.agent import AgentLabels


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None


class LabeledResource(BaseModel):
    labels: AgentLabels = Field(..., description="Agent labels stamped at creation time")
