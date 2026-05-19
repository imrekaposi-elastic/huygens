"""Background VM status monitoring."""

from __future__ import annotations

import asyncio
import socket
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from huy_libvirt_agent.app_state import AppState

logger = structlog.get_logger(__name__)


class StatusMonitor:
    def __init__(self, state: AppState) -> None:
        self._state = state
        self._task: asyncio.Task | None = None
        self._status_cache: dict[str, dict] = {}

    def register_vm(self, name: str, guest_ip_hint: str | None = None) -> None:
        self._status_cache[name] = {
            "status": "off",
            "guest_ip": guest_ip_hint,
            "last_checked_at": None,
        }

    def unregister_vm(self, name: str) -> None:
        self._status_cache.pop(name, None)

    def get_status(self, name: str) -> dict:
        return self._status_cache.get(
            name,
            {"status": "off", "guest_ip": None, "last_checked_at": None},
        )

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while True:
            try:
                await self._tick()
            except Exception:
                logger.exception("status_monitor_tick_failed")
            await asyncio.sleep(self._state.settings.status_poll_seconds)

    async def _tick(self) -> None:
        lv = self._state.libvirt
        if lv is None:
            return
        timeout = self._state.settings.ssh_probe_timeout_seconds
        for name in list(self._status_cache.keys()):
            try:
                _state_code, state_name = await lv.domain_state_async(name)
            except Exception:
                state_name = "SHUTOFF"
            guest_ip = await self._resolve_ip_async(name)
            if state_name != "RUNNING":
                new_status = "off"
            elif guest_ip and self._probe_ssh(guest_ip, timeout):
                new_status = "on"
            else:
                new_status = "degraded"
            old = self._status_cache.get(name, {}).get("status")
            now = datetime.now(UTC).isoformat()
            self._status_cache[name] = {
                "status": new_status,
                "guest_ip": guest_ip,
                "libvirt_state": state_name,
                "last_checked_at": now,
            }
            if old != new_status and old is not None:
                self._state.event_bus.publish(
                    "huy.vm.status_changed",
                    f"/hypervisors/{self._state.hostname}",
                    {
                        "name": name,
                        "status": new_status,
                        "labels": self._state.settings.agent_labels,
                    },
                )

    async def _resolve_ip_async(self, name: str) -> str | None:
        cached = self._status_cache.get(name, {})
        hint = cached.get("guest_ip")
        if hint:
            return hint
        lv = self._state.libvirt
        if lv is None:
            return None
        ips = await lv.domain_interface_addresses_async(name)
        if ips:
            return ips[0]
        meta_path = self._state.settings.data_dir / "instances" / name / "metadata.json"
        if meta_path.exists():
            import json

            meta = json.loads(meta_path.read_text())
            return meta.get("guest_ip")
        return None

    def _probe_ssh(self, ip: str, timeout: float) -> bool:
        try:
            with socket.create_connection((ip, 22), timeout=timeout):
                return True
        except OSError:
            return False
