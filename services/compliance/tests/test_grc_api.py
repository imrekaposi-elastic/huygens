"""GRC standards, packs, export, and evidence API tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from helpers import ORG_ID, org_admin_token

SAMPLE_PACK = {
    "pack_key": "test-pack-1",
    "name": "Test Pack",
    "vendor": "huygens",
    "version": "1.0",
    "payload": {
        "standards": [
            {
                "slug": "test-standard",
                "name": "Test Standard",
                "description": "For unit tests",
                "moscow": "must",
                "controls": [
                    {
                        "control_code": "T.1",
                        "name": "Control one",
                        "description": "First control",
                        "rationale": "Because tests",
                        "moscow": "must",
                    }
                ],
            }
        ]
    },
}


@pytest.mark.asyncio
async def test_grc_standards_controls_cycles(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token()}"}
    base = f"/api/v1/organizations/{ORG_ID}"

    std = await client.post(
        f"{base}/compliance-standards",
        headers=headers,
        json={"name": "ISO Lite", "slug": "iso-lite", "moscow": "must"},
    )
    assert std.status_code == 201, std.text
    std_id = std.json()["id"]

    ctrl = await client.post(
        f"{base}/compliance-standards/{std_id}/controls",
        headers=headers,
        json={
            "control_code": "A.1",
            "name": "Access control",
            "description": "Manage access",
            "rationale": "Security",
            "moscow": "must",
        },
    )
    assert ctrl.status_code == 201, ctrl.text
    ctrl_id = ctrl.json()["id"]

    cycle = await client.post(
        f"{base}/compliance-standards/{std_id}/cycles",
        headers=headers,
        json={
            "name": "2026 review",
            "starts_at": datetime.now(UTC).isoformat(),
            "ends_at": (datetime.now(UTC) + timedelta(days=90)).isoformat(),
        },
    )
    assert cycle.status_code == 201, cycle.text
    cycle_id = cycle.json()["id"]

    status = await client.get(
        f"{base}/compliance-cycles/{cycle_id}/status",
        headers=headers,
    )
    assert status.status_code == 200

    evidence = await client.post(
        f"{base}/compliance-controls/{ctrl_id}/evidence",
        headers=headers,
        data={"category": "design", "title": "Policy doc"},
        files={"file": ("policy.txt", b"policy text", "text/plain")},
    )
    assert evidence.status_code == 201, evidence.text
    ev_id = evidence.json()["id"]

    listed = await client.get(
        f"{base}/compliance-controls/{ctrl_id}/evidence",
        headers=headers,
        params={"cycle_id": cycle_id},
    )
    assert listed.status_code == 200

    download = await client.get(
        f"{base}/compliance-evidence/{ev_id}/download",
        headers=headers,
    )
    assert download.status_code == 200
    assert download.content == b"policy text"


@pytest.mark.asyncio
async def test_compliance_pack_validate_and_import(client: AsyncClient) -> None:
    headers = {"Authorization": f"Bearer {org_admin_token()}"}
    base = f"/api/v1/organizations/{ORG_ID}/compliance-packs"

    validate = await client.post(f"{base}/validate", headers=headers, json=SAMPLE_PACK)
    assert validate.status_code == 200, validate.text
    body = validate.json()
    assert not body["errors"]
    assert body["standards_to_create"] == 1
    assert body["controls_to_create"] == 1

    imported = await client.post(f"{base}/import", headers=headers, json=SAMPLE_PACK)
    assert imported.status_code == 201, imported.text
    assert imported.json()["pack_key"] == "test-pack-1"

    listed = await client.get(base, headers=headers)
    assert listed.status_code == 200
    assert any(p["pack_key"] == "test-pack-1" for p in listed.json())

    duplicate = await client.post(f"{base}/import", headers=headers, json=SAMPLE_PACK)
    assert duplicate.status_code == 400
    assert "already imported" in duplicate.json()["detail"]


@pytest.mark.asyncio
async def test_compliance_export_job(client: AsyncClient, tmp_path) -> None:
    import os

    from huy_compliance.config import get_settings

    os.environ["OBJECT_STORE_LOCAL_DIR"] = str(tmp_path)
    get_settings.cache_clear()

    headers = {"Authorization": f"Bearer {org_admin_token()}"}
    base = f"/api/v1/organizations/{ORG_ID}"

    std = await client.post(
        f"{base}/compliance-standards",
        headers=headers,
        json={"name": "Export Std", "slug": "export-std", "moscow": "must"},
    )
    assert std.status_code == 201
    std_id = std.json()["id"]

    job = await client.post(
        f"{base}/compliance-export",
        headers=headers,
        json={"export_type": "pdf", "standard_id": std_id},
    )
    assert job.status_code == 201, job.text
    job_id = job.json()["id"]

    for _ in range(30):
        await asyncio.sleep(0.05)
        status = await client.get(f"{base}/compliance-export/{job_id}", headers=headers)
        assert status.status_code == 200
        if status.json()["status"] == "completed":
            break
    else:
        pytest.fail("export job did not complete")

    download = await client.get(
        f"{base}/compliance-export/{job_id}/download",
        headers=headers,
    )
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")
