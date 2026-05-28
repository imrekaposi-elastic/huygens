# ADR 0011: Keycloak external auth and IdP group → role mapping

## Status

Accepted (Phase 2 — design)

## Context

Phase 1a delivers **local** authentication (username/password, API keys) and issues **Huygens JWTs** with `platform_roles` and `org_memberships` embedded. Registry and inventory validate those JWTs via shared `huy_auth`; they do not call IAM on every request.

[FRAMEWORK_PLAN.md](../../../FRAMEWORK_PLAN.md) requires configurable authentication backends: LOCAL, LDAP, SAML, OIDC. Phase 2 adds enterprise login while **local auth remains for break-glass** (bootstrap, IdP outage, air-gapped install per [0009](0009-air-gapped-install.md)).

Implementing SAML, LDAP, and OIDC parsers directly in `huy-iam` duplicates mature IdP functionality and increases security review surface. **Keycloak** is the preferred integration point: it federates LDAP/Active Directory and SAML IdPs, exposes OIDC to Huygens, and surfaces **group membership** in tokens.

**Requirement (product):** IdP groups must be **extracted at login** and **mapped to Huygens roles** by a **Huygens administrator** (org `admin` or `platform_admin`) — not only by Keycloak realm operators. RBAC enforcement stays in PostgreSQL + existing `ROLE_PERMISSIONS`; Keycloak does not become the sole authority for Huygens permissions.

## Decision

### 1. Split of responsibility

| Component | Responsibility |
|-----------|----------------|
| **Keycloak** | LDAP/AD/SAML federation; OIDC authorization server; MFA; group sync from directory; **groups claim** in access/ID token (via protocol mapper) |
| **huy-iam** | OIDC RP (authorization code + PKCE for console); link `external_subject` → `users`; **admin CRUD for group → role mappings**; resolve roles at login; issue **Huygens JWT** (same claim shape as Phase 1a) |
| **Registry / inventory / agents** | Unchanged: validate Huygens JWT or agent token. **No Keycloak tokens** on agent or internal service APIs. |

LDAP and SAML are configured **in Keycloak**, not in Huygens. Huygens admin UI configures **mapping tables only** (and OIDC client/realm endpoints per org or globally).

### 2. Login flow (OIDC)

1. Client calls `GET /api/v1/auth/oidc/authorize` (optional `organization_id` or realm hint).
2. Browser redirects to Keycloak; user authenticates (direct or via federated IdP).
3. Callback: `GET/POST /api/v1/auth/oidc/callback` — IAM exchanges code, validates ID token, reads `sub`, `email`, and **`groups`** (list of strings).
4. **JIT provisioning:** create or update `users` row (`auth_provider=oidc`, `external_subject`, optional `keycloak_realm`).
5. **Role resolution:** apply active `idp_group_mappings` for the org (and platform mappings if any); **union** with manually assigned org/platform roles in PostgreSQL (default: **merge**, do not replace manual assignments unless org policy flag `idp_roles_replace_manual` is set later).
6. Build `AuthContext` → issue Huygens JWT (`iss=huy-iam`, same claims as local login).
7. Optional: record last-seen groups in `user_idp_groups` for admin troubleshooting.

**Break-glass:** `auth_provider=local` users and `POST /api/v1/auth/login` remain enabled. Bootstrap `platform_admin` from env on empty DB unchanged.

### 3. Admin-configurable group → role mapping

**Table `idp_group_mappings` (PostgreSQL):**

| Column | Purpose |
|--------|---------|
| `id` | UUID |
| `organization_id` | FK; `NULL` = platform-scoped mapping |
| `idp_group_name` | Exact name or pattern source |
| `match_type` | `exact` \| `regex` |
| `huy_role` | Org role (`admin`, `compliance_admin`, …) or `platform_admin` when `organization_id` IS NULL |
| `priority` | Higher wins on conflict when using “first match” mode; default mode is **union of all matches** |
| `enabled` | Soft disable |
| `created_by`, `created_at`, … | Audit |

**API (Phase 2):**

- `GET/POST/PATCH/DELETE /api/v1/organizations/{org_id}/idp-group-mappings` — org `admin` or `platform_admin`
- `GET/POST/PATCH/DELETE /api/v1/platform/idp-group-mappings` — `platform_admin` only
- `GET /api/v1/auth/me/idp-groups` — groups from last SSO login (self) or admin preview

All mapping changes emit **`huy.audit.events`** (CloudEvents) when Kafka is available.

**Who may edit mappings:** `platform_admin` (any org + platform); org **`admin`** (own org only). Operators and compliance roles cannot edit mappings.

### 4. Group extraction from Keycloak

- Configure Keycloak **OIDC client** for `huy-iam` / console with a **Group Membership** (or custom) mapper so token contains claim `groups: string[]`.
- Prefer **realm groups** synced from LDAP; avoid overloading `realm_access.roles` for Huygens RBAC.
- Document standard realm setup in `docs/install/keycloak.md` (Phase 2 deliverable).

IAM does **not** call LDAP directly. Optional future: Admin API to list Keycloak groups via Admin REST (read-only) to help build mappings — not required for MVP of Phase 2.

### 5. Policies

| Topic | Policy |
|-------|--------|
| Multiple matching groups | **Union** of mapped Huygens roles (deduplicated) |
| No group matches | User authenticated but **no org roles** from IdP; deny org-scoped APIs unless manually assigned; login succeeds for account linking |
| Manual + IdP roles | **Merge** by default |
| API keys | Remain **local** IAM only; not Keycloak-backed |
| Agent tokens | Unchanged ([0005](0005-agent-token-vault.md)); not SSO |
| Multi-tenant | **ADR default:** one Keycloak **realm per organization** (clean isolation); alternative single realm + `org_slug` claim documented as deployment option |

### 6. Deployment

- **Development:** Keycloak service in Docker Compose (`--profile sso` or alongside `kafka`).
- **Production / air-gapped:** Keycloak image in offline bundle ([0009](0009-air-gapped-install.md)); BYO Keycloak allowed (document client/realm settings only).

## Consequences

### Phase 2 deliverables

1. ADR 0011 (this document) + Phase 2 section in [PHASED_PLAN.md](../../PHASED_PLAN.md)
2. Keycloak in Compose; example realm + group mapper
3. IAM: OIDC routes, `idp_group_mappings` model + CRUD, login role resolution, audit events
4. `docs/install/keycloak.md` — realm, mapper, example mappings
5. Console (Phase 5 ✅) consumes mapping APIs via IAM-authenticated admin UI

### Positive

- Enterprise SSO without SAML/LDAP code in Huygens
- Admins control Huygens RBAC in product UI; IdP only supplies identity + groups
- Downstream services unchanged (same JWT)

### Negative / risks

| Risk | Mitigation |
|------|------------|
| Keycloak operational burden | Compose profile; Helm in Phase 11; BYO IdP |
| Wrong group mapper → empty `groups` | Admin “last seen groups” on user; docs + health check warning |
| Over-privilege via broad regex | Audit mapping changes; require `platform_admin` for platform mappings |
| Token size with many groups | Map only required groups in Keycloak; limit claim size |

### Out of scope (Phase 2)

- SCIM user provisioning (future)
- Per-project roles from IdP groups (Phase 3+; project roles stay PG-assigned until designed)
- Replacing Huygens JWT with opaque Keycloak access token on registry/inventory APIs

## References

- [0005 Agent token vault](0005-agent-token-vault.md)
- [0009 Air-gapped install](0009-air-gapped-install.md)
- [FRAMEWORK_PLAN.md](../../../FRAMEWORK_PLAN.md) — authentication backend configuration
- Phase 1a IAM: `services/iam/`, `shared/huy_auth/`
