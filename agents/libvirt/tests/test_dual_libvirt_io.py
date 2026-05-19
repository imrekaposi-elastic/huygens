"""Dual libvirt I/O path routing tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from huy_libvirt_agent.services.dual_libvirt_client import DualLibvirtClient
from huy_libvirt_agent.services.libvirt_queue import LibvirtQueue


@pytest.fixture
def dual_client() -> tuple[DualLibvirtClient, MagicMock, MagicMock]:
    write_q = MagicMock(spec=LibvirtQueue)
    read_q = MagicMock(spec=LibvirtQueue)
    write_q.run.side_effect = lambda fn, *a, **k: fn(*a, **k)
    read_q.run.side_effect = lambda fn, *a, **k: fn(*a, **k)

    async def _async_run(fn, *a, **k):
        return fn(*a, **k)

    write_q.run_async.side_effect = _async_run
    read_q.run_async.side_effect = _async_run

    client = DualLibvirtClient("qemu:///system", write_q, read_q)
    client._read.list_networks = MagicMock(return_value=[])
    client._write.define_network_xml = MagicMock(return_value="lab0")
    client._read.list_domains = MagicMock(return_value=[])
    client._read.domain_state = MagicMock(return_value=(1, "RUNNING"))
    return client, write_q, read_q


def test_list_networks_uses_read_queue(dual_client: tuple) -> None:
    client, write_q, read_q = dual_client
    client.list_networks()
    read_q.run.assert_called()
    write_q.run.assert_not_called()


def test_define_network_uses_write_queue(dual_client: tuple) -> None:
    client, write_q, read_q = dual_client
    client.define_network_xml("<network/>")
    write_q.run.assert_called()
    read_q.run.assert_not_called()


@pytest.mark.asyncio
async def test_list_networks_async_uses_read_queue(dual_client: tuple) -> None:
    client, write_q, read_q = dual_client
    await client.list_networks_async()
    read_q.run_async.assert_called()
    write_q.run_async.assert_not_called()


@pytest.mark.asyncio
async def test_domain_state_async_uses_read_queue(dual_client: tuple) -> None:
    client, write_q, read_q = dual_client
    await client.domain_state_async("web-01")
    read_q.run_async.assert_called()
    write_q.run_async.assert_not_called()
