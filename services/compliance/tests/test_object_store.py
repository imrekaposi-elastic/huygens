from pathlib import Path

import pytest
from fastapi import HTTPException

from huy_compliance.services.object_store import _resolve_local_path


def test_resolve_local_path_accepts_nested_key(tmp_path: Path) -> None:
    base = tmp_path.resolve()
    path = _resolve_local_path(base, "huy-compliance/orgs/org-1/evidence/id/file.pdf")
    assert path.is_relative_to(base)
    assert path.name == "file.pdf"


@pytest.mark.parametrize(
    "key",
    [
        "",
        "/etc/passwd",
        "../outside",
        "huy-compliance/../../outside",
        r"foo\bar",
    ],
)
def test_resolve_local_path_rejects_unsafe_keys(tmp_path: Path, key: str) -> None:
    base = tmp_path.resolve()
    with pytest.raises(HTTPException) as exc_info:
        _resolve_local_path(base, key)
    assert exc_info.value.status_code == 400
