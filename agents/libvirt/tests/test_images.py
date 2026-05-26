"""Managed image API tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def sample_disk(tmp_data_dir: Path) -> Path:
    import_dir = tmp_data_dir / "images" / "import"
    import_dir.mkdir(parents=True, exist_ok=True)
    disk = import_dir / "base.qcow2"
    disk.write_bytes(b"fake-qcow2-content")
    return disk


def test_image_crud(client: TestClient, auth_headers: dict, sample_disk: Path) -> None:
    digest = hashlib.sha256(sample_disk.read_bytes()).hexdigest()
    create = client.post(
        "/api/v1/images",
        headers=auth_headers,
        json={
            "name": "test-base",
            "source": str(sample_disk),
            "sha256": digest,
            "fetch": True,
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["name"] == "test-base"
    assert body["status"] == "ready"
    assert body["size_bytes"] == sample_disk.stat().st_size

    listed = client.get("/api/v1/images", headers=auth_headers)
    assert listed.status_code == 200
    assert any(i["name"] == "test-base" for i in listed.json())

    got = client.get("/api/v1/images/test-base", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["cached_path"]

    dup = client.post(
        "/api/v1/images",
        headers=auth_headers,
        json={"name": "test-base", "source": str(sample_disk), "fetch": False},
    )
    assert dup.status_code == 409

    deleted = client.delete("/api/v1/images/test-base", headers=auth_headers)
    assert deleted.status_code == 204

    missing = client.get("/api/v1/images/test-base", headers=auth_headers)
    assert missing.status_code == 404


def test_image_update_refetch(client: TestClient, auth_headers: dict, sample_disk: Path) -> None:
    client.post(
        "/api/v1/images",
        headers=auth_headers,
        json={"name": "refetch-img", "source": str(sample_disk), "fetch": True},
    )
    patch = client.patch(
        "/api/v1/images/refetch-img",
        headers=auth_headers,
        json={"refetch": True},
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "ready"
