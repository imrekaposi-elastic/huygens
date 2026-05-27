# Kibana compliance pack (Phase 7 spike)

Phase 7 ships transactional compliance in PostgreSQL (`huy-compliance`) and structured logs for catalog/check/criticality changes. Elasticsearch ECS views and a Kibana “Huygens Compliance” app remain optional (Phase 8+).

## Current PG/API sources (MVP — index later)

| Source | Use in Kibana |
|--------|----------------|
| `compliance_audit` structlog events | Who changed catalog, checks, assignments |
| Compliance explorer aggregates | Gap analysis (missing standards) — via API or future sync |
| Infrastructure provider/region profiles | Placement inheritance counts |
| Project aggregate membership | Projects where all children satisfy a standard |
| Check alerter output | Expiring / expired checks |

Console MVP: [phase7 operations](../../operations/phase7-compliance-and-lifecycle-guards.md).

## Intended surfaces

- Asset criticality and org catalog items (synced or queried via API)
- Compliance check expiry and owner accountability
- Audit trail correlation (`compliance_audit` structlog events → ECS)
- Placement rationale exports for auditor workflows

## Next steps

1. Index `compliance_audit` events from control-plane OTLP/log shipping (Phase 8).
2. Prototype Lens/ES|QL dashboards: checks expiring in 30 days, assignments by project.
3. Map Kibana roles to Huygens `compliance_admin`, `compliance_reader`, `auditor` via OIDC group claims.

Air-gapped installs: export saved objects NDJSON; no Fleet required for read-only compliance dashboards.
