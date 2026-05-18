"""Audit log tests."""

import json
from pathlib import Path

from fastapi.testclient import TestClient


def test_audit_record_written(client: TestClient, auth_headers: dict, tmp_data_dir: Path) -> None:
    client.get("/api/v1/agent", headers={**auth_headers, "X-Actor": "test-suite"})
    audit_dir = tmp_data_dir / "audit"
    files = list(audit_dir.glob("*.jsonl"))
    assert files
    line = files[0].read_text().strip().split("\n")[-1]
    record = json.loads(line)
    assert record["actor"] == "test-suite"
    assert record["method"] == "GET"
    assert record["agent_labels"]["country"] == "NL"
    assert "request_body_sha256" in record
