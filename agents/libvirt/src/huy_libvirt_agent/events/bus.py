"""In-process domain event bus."""

from __future__ import annotations

from typing import Protocol

import structlog

from huy_libvirt_agent.events.models import DomainEvent

logger = structlog.get_logger(__name__)


class EventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None: ...


class NoopPublisher:
    def publish(self, event: DomainEvent) -> None:
        pass


class FileEventPublisher:
    def __init__(self, events_dir) -> None:
        from pathlib import Path

        self._dir = Path(events_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def publish(self, event: DomainEvent) -> None:
        from datetime import UTC, datetime

        day = datetime.now(UTC).strftime("%Y-%m-%d")
        path = self._dir / f"{day}.jsonl"
        with path.open("a") as f:
            f.write(event.model_dump_json() + "\n")


class EventBus:
    def __init__(self, publishers: list[EventPublisher] | None = None) -> None:
        self._publishers = publishers or []

    def add_publisher(self, publisher: EventPublisher) -> None:
        self._publishers.append(publisher)

    def publish(
        self,
        event_type: str,
        source: str,
        data: dict,
        correlation_id: str | None = None,
    ) -> DomainEvent:
        event = DomainEvent(
            type=event_type,
            source=source,
            data=data,
            correlation_id=correlation_id,
        )
        for pub in self._publishers:
            try:
                pub.publish(event)
            except Exception:
                logger.exception("event_publish_failed", event_type=event_type)
        logger.info("domain_event", event_type=event_type, correlation_id=correlation_id)
        return event
