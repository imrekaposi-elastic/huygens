"""Agent settings and label schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentLabels(BaseModel):
    country: str = Field(..., description="ISO 3166-1 alpha-2 country code when possible")
    city: str
    company: str


class AgentSettingsResponse(BaseModel):
    hostname: str
    version: str
    settings: AgentLabels
    libvirt_uri: str
    data_dir: str
