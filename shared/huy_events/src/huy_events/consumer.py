"""Broadcast Kafka consumer — unique group.id per instance (all pods see all messages)."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiokafka import AIOKafkaConsumer

from huy_events.config import KafkaSettings
from huy_events.tracing import kafka_consumer_span

logger = structlog.get_logger(__name__)

MessageHandler = Callable[[dict[str, Any]], Awaitable[None]]


class HuyBroadcastConsumer:
    """Subscribe with a dedicated consumer group so every replica receives every message."""

    def __init__(
        self,
        settings: KafkaSettings,
        *,
        group_id: str,
        topics: list[str],
        handler: MessageHandler,
    ) -> None:
        self._settings = settings
        self._group_id = group_id
        self._topics = topics
        self._handler = handler
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self) -> None:
        if self._consumer is not None:
            return
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._settings.bootstrap_servers,
            group_id=self._group_id,
            client_id=self._settings.resolved_client_id(self._group_id),
            value_deserializer=lambda raw: json.loads(raw.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        await self._consumer.start()
        logger.info("kafka_broadcast_consumer_started", group_id=self._group_id, topics=self._topics)

    async def stop(self) -> None:
        if self._consumer is None:
            return
        await self._consumer.stop()
        self._consumer = None
        logger.info("kafka_broadcast_consumer_stopped", group_id=self._group_id)

    async def run_forever(self) -> None:
        if self._consumer is None:
            msg = "Kafka consumer not started; call start() first"
            raise RuntimeError(msg)
        async for message in self._consumer:
            try:
                with kafka_consumer_span(
                    message.topic,
                    bootstrap=self._settings.kafka_bootstrap,
                ):
                    await self._handler(message.value)
            except Exception as exc:
                logger.exception(
                    "kafka_message_handler_failed",
                    topic=message.topic,
                    partition=message.partition,
                    error=str(exc),
                )
