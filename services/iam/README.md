# huy-iam

Identity and access management for Huygens (Phase 1a).

## Scope

- Local users and passwords (LDAP/SAML/OIDC in Phase 2)
- Organization-scoped roles: `platform_admin`, `admin`, `compliance_engineer`, project roles
- JWT issuance for console and service-to-service calls

## Run (scaffold)

```bash
cd services/iam
pip install -e .
huy-iam
```

Default: `http://127.0.0.1:8081`

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL (Phase 1a) |
| `JWT_SECRET` | Signing key |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Optional OTLP |

See [ADR 0005](../../docs/architecture/adrs/0005-agent-token-vault.md) for agent tokens (registry, not IAM).
