# Elasticsearch ingest for SSH sessions

Installed automatically by the `elasticsearch-setup` Compose service when using `--profile observability`.

## Data streams

| Data stream | Source | Content |
|-------------|--------|---------|
| `huy-sessions` | `huy.session.events` + `huy.session.recording` | Session metadata + terminal I/O |
| `huy-audit` | `huy.audit.events` | Compliance audit events |

Data streams are **recreated automatically** after deletion when `elasticsearch-setup` runs (or on first ingest). Backing indices roll over via ILM (`huy-sessions-ilm`, `huy-audit-ilm`).

Legacy daily indices (`huy-sessions-2026.*`, `huy-session-terminal-*`) are no longer written to.

## Pipelines

| Pipeline | Data stream | Purpose |
|----------|-------------|---------|
| `huy-sessions-ecs` | `huy-sessions` | Session open/close metadata (ECS) |
| `huy-session-terminal` | `huy-sessions` | Terminal I/O lines (`event.dataset: huy.session.terminal`) |
| `huy-audit-ecs` | `huy-audit` | Compliance audit events (ECS) |

## Terminal recording fields

Each asciicast line becomes one document (batched on Enter for input, on newline for output):

- `@timestamp` — cast line time converted to ISO8601
- `session.id` — correlates metadata and terminal docs
- `terminal.stream` — `i` (command typed) or `o` (shell output)
- `terminal.plaintext` — human-readable text (ANSI stripped); **search this field**
- `terminal.input` / `terminal.output` — same plaintext, split by direction

## Session metadata fields

Each open/close CloudEvent becomes one document:

- `event.action` — `session.open` / `session.close`
- `event.dataset` — `huy.session`
- `session.id`, `organization.id`, `huy.project.id`
- `huy.session.started_at`, `huy.session.ended_at`, `huy.session.status`

## Kibana Discover

Data views (created by `kibana-setup`):

- **Huy SSH Sessions** → `huy-sessions`
- **Huy Audit** → `huy-audit`

| What | KQL filter |
|------|------------|
| Session start/end | `event.action: (session.open or session.close)` |
| Commands typed | `event.action: session.terminal and terminal.stream: i` |
| Shell output | `event.action: session.terminal and terminal.stream: o` |
| One session | `session.id: "<uuid>"` |

## Manual install / recreate after delete

```bash
SETUP_DIR=./docker/observability/elasticsearch \
  ELASTICSEARCH_URL=http://127.0.0.1:9200 \
  ELASTIC_PASSWORD=changeme-dev-only \
  ./docker/observability/elasticsearch/setup.sh

KIBANA_URL=http://127.0.0.1:5601 \
  ELASTIC_PASSWORD=changeme-dev-only \
  ./docker/observability/kibana/setup.sh

docker compose --profile observability restart logstash
```

New SSH sessions (or Kafka replay) populate the stream after setup.
