"""Image store streaming tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest

from huy_libvirt_agent.services.image_store import ImageStore


def test_verify_sha256_streams_file(tmp_path: Path) -> None:
    path = tmp_path / "big.bin"
    payload = b"x" * (3 * 1024 * 1024)
    path.write_bytes(payload)
    ImageStore.verify_sha256(path, hashlib.sha256(payload).hexdigest())


def test_download_streams_to_disk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b"qcow2-chunk-" * 100_000
    expected = hashlib.sha256(payload).hexdigest()
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, content=payload),
    )

    original_client = httpx.Client

    class PatchedClient(original_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", PatchedClient)
    dest = tmp_path / "image.qcow2"
    store = ImageStore(tmp_path / "cache", download_timeout=30)
    store.download_url_to_path("https://example.invalid/image.qcow2", dest, expected)
    assert dest.read_bytes() == payload


def test_download_rejects_bad_checksum(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b"small-image"
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, content=payload),
    )

    original_client = httpx.Client

    class PatchedClient(original_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", PatchedClient)
    dest = tmp_path / "image.qcow2"
    store = ImageStore(tmp_path / "cache", download_timeout=30)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        store.download_url_to_path(
            "https://example.invalid/image.qcow2",
            dest,
            "0" * 64,
        )
    assert not dest.exists()
    assert not dest.with_suffix(".part").exists()
