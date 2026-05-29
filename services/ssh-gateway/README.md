# SSH gateway (`huy-ssh-gateway`)

Go service (port **8087**) for audited VM SSH (Phase 9).

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness |
| `POST` | `/api/v1/ssh/sessions` | Create session (JWT) |
| `GET` | `/api/v1/ssh/sessions` | List sessions |
| `GET` | `/api/v1/ssh/sessions/{id}` | Session metadata |
| `GET` | `/api/v1/ssh/sessions/{id}/recording` | Asciicast replay |
| `GET` | `/api/v1/ssh/sessions/{id}/ws` | WebSocket PTY bridge |

## Configuration

| Variable | Default |
|----------|---------|
| `HUY_SSH_GATEWAY_HOST` | `0.0.0.0:8087` |
| `JWT_SECRET` / `JWT_ISSUER` | Same as IAM |
| `IAM_URL` | `http://iam:8081` |
| `IAM_SERVICE_TOKEN` | `dev-iam-service-token` |
| `INVENTORY_URL` | `http://inventory:8083` |
| `SSH_RECORDING_DIR` | `/data/ssh-recordings` |
| `KAFKA_BOOTSTRAP` | `kafka:9092` |

## Tests

```bash
cd services/ssh-gateway && go test ./...
```
