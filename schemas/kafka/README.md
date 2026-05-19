# Kafka event schemas

CloudEvents 1.0 envelope with JSON `data` payloads. Producers set:

- `specversion`: `1.0`
- `type`: e.g. `com.huygens.agent.vm.state_changed`
- `source`: URI of producer (`/agents/{agent_id}` or service name)
- `id`: UUID
- `time`: RFC3339
- `datacontenttype`: `application/json`
- `dataschema`: URI to schema file in this directory

## Topics

| Topic | Schema |
|-------|--------|
| `huy.agent.events` | [agent-event.schema.json](agent-event.schema.json) |
| `huy.inventory.snapshots` | [inventory-snapshot.schema.json](inventory-snapshot.schema.json) |
| `huy.audit.events` | [audit-event.schema.json](audit-event.schema.json) |

## Versioning

Bump `data.version` (integer) for breaking `data` shape changes. Consumers should ignore unknown fields.
