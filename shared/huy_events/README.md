# huy-events

Shared Kafka and CloudEvents helpers for Huygens control-plane services.

## Configuration

| Variable | Description |
|----------|-------------|
| `KAFKA_BOOTSTRAP` | Comma-separated broker list (default `kafka:9092`) |
| `KAFKA_CLIENT_ID` | Optional client id (default `huy-{service}`) |

## Usage

```python
from huy_events import HuyKafkaProducer, KafkaSettings, build_envelope, TOPIC_INVENTORY_SNAPSHOTS

settings = KafkaSettings()
producer = HuyKafkaProducer(settings, service_name="inventory")
await producer.start()
await producer.send(TOPIC_INVENTORY_SNAPSHOTS, build_envelope(...))
await producer.stop()
```

Topic constants include `TOPIC_NETWORK_LINKS` (`huy.network.links`) for Phase 6 link lifecycle events from projects.

See [ADR 0004](../../docs/architecture/adrs/0004-kafka-event-bus.md).
