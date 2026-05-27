"""Canonical resource keys for assignments and explainability."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceRef:
    resource_type: str
    project_id: str
    agent_id: str | None = None
    name: str | None = None

    def key(self) -> str:
        if self.resource_type == "project":
            return f"project:{self.project_id}"
        if self.resource_type == "vm":
            return f"vm:{self.project_id}:{self.agent_id}:{self.name}"
        if self.resource_type == "network":
            return f"network:{self.project_id}:{self.agent_id}:{self.name}"
        raise ValueError(f"Unsupported resource_type: {self.resource_type}")

    @classmethod
    def from_parts(
        cls,
        resource_type: str,
        *,
        project_id: str,
        agent_id: str | None = None,
        name: str | None = None,
    ) -> ResourceRef:
        resource_type = resource_type.lower()
        if resource_type == "project":
            return cls(resource_type=resource_type, project_id=project_id)
        if resource_type in ("vm", "network"):
            if not agent_id or not name:
                raise ValueError("agent_id and name required for vm/network resources")
            return cls(
                resource_type=resource_type,
                project_id=project_id,
                agent_id=agent_id,
                name=name,
            )
        raise ValueError(f"Unsupported resource_type: {resource_type}")
