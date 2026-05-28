"""Async Kafka producer with JSON CloudEvents payloads."""

from __future__ import annotations

import json
from typing import Any

import structlog
from aiokafka import AIOKafkaProducer

from huy_events.config import KafkaSettings
from huy_events.tracing import kafka_producer_span

logger = structlog.get_logger(__name__)


class HuyKafkaProducer:
    def __init__(self, settings: KafkaSettings, *, service_name: str) -> None:
        self._settings = settings
        self._service_name = service_name
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if self._producer is not None:
            return
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._settings.bootstrap_servers,
            client_id=self._settings.resolved_client_id(self._service_name),
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )
        await self._producer.start()
        logger.info(
            "kafka_producer_started",
            bootstrap=self._settings.kafka_bootstrap,
            client_id=self._settings.resolved_client_id(self._service_name),
        )

    async def stop(self) -> None:
        if self._producer is None:
            return
        await self._producer.stop()
        self._producer = None
        logger.info("kafka_producer_stopped")

    async def send(self, topic: str, envelope: dict[str, Any], *, key: str | None = None) -> None:
        if self._producer is None:
            msg = "Kafka producer not started; call start() first"
            raise RuntimeError(msg)
        key_bytes = key.encode("utf-8") if key is not None else None
        with kafka_producer_span(topic, bootstrap=self._settings.kafka_bootstrap):
            await self._producer.send_and_wait(topic, envelope, key=key_bytes)
