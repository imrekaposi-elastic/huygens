"""Network list readonly/deletable flags respect agent vnet metadata."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from huy_libvirt_agent.app_state import AppState
from huy_libvirt_agent.config import Settings
from huy_libvirt_agent.services.network_service import NetworkService


def _service(data_dir: Path) -> NetworkService:
    settings = Settings(
        agent_token="t",
        agent_country="NL",
        agent_city="Amsterdam",
        agent_company="Test",
        data_dir=data_dir,
    )
    iptables = MagicMock()
    iptables.checksum_for_vnet.return_value = None
    state = AppState(
        settings=settings,
        libvirt=MagicMock(connected=True),
        iptables=iptables,
    )
    return NetworkService(state)


def test_managed_lab_network_not_readonly_when_libvirt_lists_it(tmp_path: Path) -> None:
    (tmp_path / "vnets" / "lab0").mkdir(parents=True)
    svc = _service(tmp_path)
    lv_info = {
        "name": "lab0",
        "uuid": "u",
        "active": True,
        "bridge": "br-lab0",
        # Stale/wrong flags from libvirt layer must not override agent metadata.
        "readonly": True,
        "deletable": False,
    }
    resp = svc._network_response("lab0", lv_info)
    assert resp.readonly is False
    assert resp.deletable is True


def test_default_stays_readonly(tmp_path: Path) -> None:
    svc = _service(tmp_path)
    resp = svc._network_response(
        "default",
        {"name": "default", "uuid": "u", "active": True, "bridge": "virbr0"},
    )
    assert resp.readonly is True
    assert resp.deletable is False
