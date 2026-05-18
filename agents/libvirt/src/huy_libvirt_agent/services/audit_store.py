"""Append-only request audit log."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AuditStore:
    def __init__(self, audit_dir: Path) -> None:
        self._dir = audit_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict[str, Any]) -> str:
        audit_id = str(uuid.uuid4())
        record["audit_id"] = audit_id
        record["timestamp"] = datetime.now(UTC).isoformat()
        day = datetime.now(UTC).strftime("%Y-%m-%d")
        path = self._dir / f"{day}.jsonl"
        with path.open("a") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return audit_id
