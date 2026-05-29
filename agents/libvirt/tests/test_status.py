"""VM status logic tests."""

import socket
from unittest.mock import patch

from huy_libvirt_agent.services.status_monitor import StatusMonitor


class _FakeState:
    settings = type("S", (), {"status_poll_seconds": 1, "ssh_probe_timeout_seconds": 0.1})()
    hostname = "test"
    event_bus = type("B", (), {"publish": lambda *a, **k: None})()
    libvirt = None


def test_ssh_probe_success() -> None:
    mon = StatusMonitor(_FakeState())  # type: ignore
    with patch.object(socket, "create_connection", return_value=__import__("contextlib").nullcontext()):
        assert mon._probe_ssh("127.0.0.1", 1.0) is True


def test_ssh_probe_failure() -> None:
    mon = StatusMonitor(_FakeState())  # type: ignore
    with patch.object(socket, "create_connection", side_effect=OSError):
        assert mon._probe_ssh("127.0.0.1", 1.0) is False


def test_bootstrap_known_vms_from_instances(tmp_path) -> None:
    mon = StatusMonitor(_FakeState())  # type: ignore
    inst = tmp_path / "instances" / "web-01"
    inst.mkdir(parents=True)
    (inst / "metadata.json").write_text('{"guest_ip": "10.0.0.42"}')
    added = mon.bootstrap_known_vms(None, tmp_path)
    assert added == 1
    assert mon.get_status("web-01")["guest_ip"] == "10.0.0.42"
