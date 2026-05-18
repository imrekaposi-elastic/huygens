"""Libvirt work queue tests."""

from __future__ import annotations

import threading
import time

import pytest

from huy_libvirt_agent.services.libvirt_client import LibvirtError
from huy_libvirt_agent.services.libvirt_queue import LibvirtQueue


def test_queue_serializes_calls() -> None:
    q = LibvirtQueue(workers=1, max_pending=8, call_timeout_seconds=5.0)
    order: list[int] = []
    active = threading.Event()

    def work(n: int) -> int:
        assert not active.is_set(), "only one libvirt job at a time"
        active.set()
        order.append(n)
        time.sleep(0.02)
        active.clear()
        return n

    results = [q.run(work, i) for i in range(4)]
    assert results == [0, 1, 2, 3]
    assert order == [0, 1, 2, 3]
    q.shutdown()


def test_queue_full_rejects() -> None:
    q = LibvirtQueue(workers=1, max_pending=1, call_timeout_seconds=5.0)
    started = threading.Event()

    def slow() -> None:
        started.set()
        time.sleep(2)

    t = threading.Thread(target=lambda: q.run(slow))
    t.start()
    assert started.wait(timeout=2)
    with pytest.raises(LibvirtError) as exc:
        q.run(lambda: None)
    assert exc.value.code == "LIBVIRT_QUEUE_FULL"
    t.join(timeout=5)
    q.shutdown()


def test_metrics_expose_queue_depth(client) -> None:
    from fastapi.testclient import TestClient

    c: TestClient = client
    r = c.get("/metrics")
    assert "huy_libvirt_queue_pending" in r.text
    assert "huy_libvirt_queue_max_pending" in r.text
