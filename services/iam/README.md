# huy-iam

Identity and access management for Huygens (**Phase 1a–2**).

## Features

- **Local auth:** username/password login → JWT (HS256)
- **Keycloak OIDC (Phase 2):** authorization code + PKCE; groups → configurable role mapping
- **API keys:** `Authorization: Bearer huy_…` (local users only)
- **Multi-tenant orgs** with org-scoped roles
- **Platform admin:** cross-org; register agents (Phase 1); create orgs; assign `platform_admin`
- **RBAC:** permission checks via `huy_iam.rbac` / `huy_auth` for registry/inventory

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
# Local login
curl -s -X POST http://127.0.0.1:8081/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"platform-admin","password":"change-me-bootstrap"}' | jq .
```

### Keycloak SSO (optional)

See [docs/install/keycloak.md](../../docs/install/keycloak.md). Enable `OIDC_ENABLED=true` and use:

- `GET /api/v1/auth/oidc/authorize?organization_id={org_uuid}`
- `GET /api/v1/auth/oidc/callback?code=…&state=…`

## API summary

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/v1/auth/login` | — |
| GET | `/api/v1/auth/me` | JWT or API key |
| GET | `/api/v1/auth/me/idp-groups` | JWT |
| GET | `/api/v1/auth/oidc/authorize` | — (requires `OIDC_ENABLED`) |
| GET | `/api/v1/auth/oidc/callback` | — |
| POST | `/api/v1/auth/api-keys` | JWT |
| GET/POST/PATCH/DELETE | `/api/v1/organizations/{id}/idp-group-mappings` | org `admin` |
| GET/POST/PATCH/DELETE | `/api/v1/platform/idp-group-mappings` | `platform_admin` |
| POST | `/api/v1/organizations` | `platform_admin` |
| GET | `/api/v1/organizations` | member or `platform_admin` |

OpenAPI: http://127.0.0.1:8081/docs

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | SQLite (dev) or PostgreSQL |
| `JWT_SECRET` / `JWT_ISSUER` | Huygens JWT (shared with registry/inventory) |
| `OIDC_ENABLED` | Enable Keycloak login |
| `OIDC_ISSUER` | e.g. `http://127.0.0.1:8080/realms/huygens` |
| `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` | Keycloak client |
| `OIDC_REDIRECT_URI` | Callback URL registered in Keycloak |

## Tests

```bash
make test
```

## References

- [ADR 0011 — Keycloak group mapping](../../docs/architecture/adrs/0011-keycloak-group-role-mapping.md)
- [ADR 0005 — Agent tokens](../../docs/architecture/adrs/0005-agent-token-vault.md)
