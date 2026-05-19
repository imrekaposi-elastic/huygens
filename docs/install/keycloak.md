# Keycloak setup for Huygens (Phase 2)

Huygens uses **Keycloak** for enterprise SSO (LDAP, SAML, OIDC federation). Huygens IAM remains the **RBAC authority**: admins map IdP **groups** to Huygens **roles** in the control plane.

## Docker Compose (development)

```bash
cp compose.env.example .env
docker compose --profile sso up -d --build
```

| Service | URL |
|---------|-----|
| Keycloak | http://127.0.0.1:8080 (admin `admin` / `admin`) |
| IAM | http://127.0.0.1:8081 |
| Realm | `huygens` (imported from `docker/keycloak/huygens-realm.json`) |

Set on **iam** service (see `compose.env.example`):

- `OIDC_ENABLED=true`
- `OIDC_ISSUER=http://keycloak:8080/realms/huygens` (inside Compose network)
- For browser redirects from host, authorize URL uses Keycloak at `http://127.0.0.1:8080`

## Dev test user

| Field | Value |
|-------|--------|
| Username | `sso-user` |
| Password | `sso-user-dev` |
| Groups | `acme-admins` |

## Admin workflow

1. **Create organization** in IAM (platform admin): e.g. slug `acme`.
2. **Create group mapping** (org admin or platform admin):

```bash
curl -s -X POST "http://127.0.0.1:8081/api/v1/organizations/{org_id}/idp-group-mappings" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"idp_group_name":"acme-admins","match_type":"exact","huy_role":"admin"}'
```

3. **SSO login**:

```bash
# Start login (returns Keycloak authorization URL)
curl -s "http://127.0.0.1:8081/api/v1/auth/oidc/authorize?organization_id={org_id}"

# Complete in browser; callback returns Huygens JWT:
# GET /api/v1/auth/oidc/callback?code=...&state=...
```

4. **Inspect last IdP groups** for your user:

```bash
curl -s http://127.0.0.1:8081/api/v1/auth/me/idp-groups \
  -H "Authorization: Bearer $TOKEN"
```

## Platform-level mapping

Map Keycloak group `huy-platform-ops` → `platform_admin`:

```bash
POST /api/v1/platform/idp-group-mappings
{"idp_group_name":"huy-platform-ops","huy_role":"platform_admin"}
```

## Keycloak configuration notes

- **Groups claim:** realm import includes `oidc-group-membership-mapper` on client `huy-iam` (claim `groups`).
- **LDAP / SAML:** configure user federation in Keycloak Admin → User federation; sync groups into realm groups.
- **Production:** use HTTPS, rotate client secret, restrict redirect URIs; BYO Keycloak is supported (set `OIDC_*` env on IAM).

## Break-glass

Local IAM users (`auth_provider=local`) and `POST /api/v1/auth/login` remain enabled. Bootstrap `platform-admin` from `BOOTSTRAP_ADMIN_*` env vars.

See [ADR 0011](../architecture/adrs/0011-keycloak-group-role-mapping.md).
