"""Export PDF generator unit tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from huy_compliance.services.export_service import _pdf_bytes_from_lines, _render_export_pdf


def test_pdf_bytes_from_lines_produces_valid_header() -> None:
    pdf = _pdf_bytes_from_lines(["Line one", "Line two"])
    assert pdf.startswith(b"%PDF-1.4")
    assert b"%%EOF" in pdf


@pytest.mark.asyncio
async def test_render_export_pdf_all_standards(client) -> None:
    from huy_compliance.db import get_session_factory

    _ = client
    factory = get_session_factory()
    async with factory() as session:
        pdf = await _render_export_pdf(
            session,
            "11111111-1111-1111-1111-111111111111",
            job_id="job-1",
            generated_by="tester",
            generated_at=datetime.now(UTC),
            standard_id=None,
            cycle_id=None,
        )
    assert pdf.startswith(b"%PDF")
