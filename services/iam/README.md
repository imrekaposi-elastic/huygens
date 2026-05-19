# huy-iam

Identity and access management for Huygens (**Phase 1a**).

## Features

- **Local auth:** username/password login → JWT (HS256)
- **API keys:** `Authorization: Bearer huy_…` (same as JWT on protected routes)
- **Multi-tenant orgs** with org-scoped roles
- **Platform admin:** cross-org; register agents (Phase 1); create orgs; assign `platform_admin`
- **RBAC:** permission checks via `huy_iam.rbac` for reuse by registry/inventory (Phase 1)
- **Project role stubs:** assign project roles before project service exists (Phase 3)

### Built-in roles

| Scope | Roles |
|-------|--------|
| Platform | `platform_admin` |
| Organization | `admin`, `compliance_admin`, `compliance_engineer` |
| Project (stub) | `project_admin`, `operator`, `auditor`, `compliance_reader`, … |

## Quick start

```bash
cd services/iam
cp .env.example .env
make install
make run
```

On first start with an empty database, a **bootstrap** `platform_admin` user is created from `BOOTSTRAP_ADMIN_*` env vars.

```bash
# Login
curl -s -X POST http://127.0.0.1:8081/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"platform-admin","password":"change-me-bootstrap"}' | jq .

# Create organization
export TOKEN=…
curl -s -X POST http://127.0.0.1:8081/api/v1/organizations \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Acme","slug":"acme"}' | jq .
```

OpenAPI: http://127.0.0.1:8081/docs

## API summary

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/v1/auth/login` | — |
| GET | `/api/v1/auth/me` | JWT or API key |
| POST | `/api/v1/auth/api-keys` | JWT or API key |
| POST | `/api/v1/organizations` | `platform_admin` |
| GET | `/api/v1/organizations` | member or `platform_admin` |
| POST | `/api/v1/organizations/{id}/users` | org `admin` or `platform_admin` |
| PUT | `/api/v1/organizations/{id}/users/{uid}/roles` | org `admin` or `platform_admin` |
| POST | `/api/v1/users/{id}/platform-roles` | `platform_admin` |

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite://…` (dev) or `postgresql+asyncpg://…` |
| `JWT_SECRET` | HS256 signing key |
| `BOOTSTRAP_ADMIN_*` | First-run platform admin |

## Tests

```bash
make test
```

## JWT claims (for other services)

```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "username": "user",
  "platform_roles": ["platform_admin"],
  "org_memberships": [{"organization_id": "…", "roles": ["admin"]}],
  "project_roles": [{"organization_id": "…", "project_id": "…", "role": "operator"}]
}
```

Validate with the same `JWT_SECRET` and `JWT_ISSUER`, or import helpers from `huy_iam.rbac` and `huy_iam.security.decode_access_token`.

See [ADR 0005](../../docs/architecture/adrs/0005-agent-token-vault.md) for **agent** tokens (registry service, not IAM).
