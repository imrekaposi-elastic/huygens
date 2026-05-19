"""Shared application state."""

from __future__ import annotations

import socket
from dataclasses import dataclass, field

from huy_libvirt_agent.config import Settings
from huy_libvirt_agent.events.bus import EventBus
from huy_libvirt_agent.services.audit_store import AuditStore
from huy_libvirt_agent.services.breakout_service import BreakoutService
from huy_libvirt_agent.services.dnat_service import DnatService
from huy_libvirt_agent.services.iptables_manager import IptablesManager
from huy_libvirt_agent.services.dual_libvirt_client import DualLibvirtClient
from huy_libvirt_agent.services.libvirt_queue import LibvirtQueue
from huy_libvirt_agent.services.status_monitor import StatusMonitor


@dataclass
class AppState:
    settings: Settings
    libvirt_write_queue: LibvirtQueue | None = None
    libvirt_read_queue: LibvirtQueue | None = None
    libvirt: DualLibvirtClient | None = None
    event_bus: EventBus = field(default_factory=EventBus)
    audit_store: AuditStore | None = None
    iptables: IptablesManager | None = None
    breakout: BreakoutService | None = None
    dnat: DnatService | None = None
    monitor: StatusMonitor = field(default_factory=lambda: None)  # type: ignore
    hostname: str = ""

    def __post_init__(self) -> None:
        self.hostname = socket.gethostname()
        if self.monitor is None:
            self.monitor = StatusMonitor(self)

    @property
    def libvirt_queue(self) -> LibvirtQueue | None:
        """Write queue (backward compatible)."""
        return self.libvirt_write_queue

    @classmethod
    def from_settings(cls, settings: Settings) -> AppState:
        settings.ensure_data_dirs()
        write_queue = LibvirtQueue(
            workers=settings.libvirt_queue_workers,
            max_pending=settings.libvirt_queue_max_pending,
            call_timeout_seconds=settings.libvirt_queue_timeout_seconds,
        )
        read_queue = LibvirtQueue(
            workers=settings.libvirt_read_queue_workers,
            max_pending=settings.libvirt_read_queue_max_pending,
            call_timeout_seconds=settings.libvirt_read_queue_timeout_seconds,
        )
        lv = DualLibvirtClient(settings.libvirt_uri, write_queue, read_queue)
        bus = EventBus()
        from huy_libvirt_agent.events.bus import FileEventPublisher, NoopPublisher

        if settings.event_bus == "file":
            bus.add_publisher(FileEventPublisher(settings.data_dir / "events"))
        elif settings.event_bus == "none":
            bus.add_publisher(NoopPublisher())
        audit = AuditStore(settings.data_dir / "audit") if settings.audit_enabled else None
        iptables = IptablesManager(
            settings.iptables_backend,
            settings.data_dir / "vnets",
        )
        breakout = BreakoutService(
            settings.data_dir / "vnets",
            settings.wg_config_dir,
            iptables,
        )
        dnat = DnatService(settings.data_dir / "vnets", breakout, settings.agent_labels)
        state = cls(
            settings=settings,
            libvirt_write_queue=write_queue,
            libvirt_read_queue=read_queue,
            libvirt=lv,
            event_bus=bus,
            audit_store=audit,
            iptables=iptables,
            breakout=breakout,
            dnat=dnat,
        )
        return state
