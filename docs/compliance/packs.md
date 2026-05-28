# Compliance packs (Phase 7+)

Compliance packs are JSON bundles that seed an organization with **standards** and **controls** under the GRC model.

## Goals

- Rapid bootstrap for common frameworks (ISO 27001, BIO, DigiD assessment, …)
- Preserve provenance (pack record stores `pack_key`, version, vendor, and raw JSON)
- Allow organizations to extend or override after import

## API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `.../compliance-packs/validate` | Dry-run: counts standards/controls to create; returns validation errors |
| `POST` | `.../compliance-packs/import` | Validate, then create pack record and **apply** payload (standards + controls) |
| `GET` | `.../compliance-packs` | List imported packs for the org |

Console: **Compliance → GRC** — paste JSON, **Dry-run validate**, then **Apply import**.

### Apply behavior

- Rejects duplicate `pack_key` for the same org (HTTP 409).
- For each standard in `payload.standards`: creates `OrgComplianceStandard` (slug from payload or derived from name).
- For each control under that standard: creates `OrgComplianceControl` with optional `control_code`, `rationale`, MoSCoW.
- Fails if a standard slug already exists in the org (no silent merge).
- Records an audit event `pack.import`.

Pack JSON is also stored on `OrgCompliancePack.raw_json` for provenance.

## JSON shape

```json
{
  "pack_key": "iso27001:2022",
  "name": "ISO 27001:2022",
  "vendor": "iso",
  "version": "2022",
  "standards": [
    {
      "slug": "iso27001-2022",
      "name": "ISO 27001:2022",
      "description": "Information security management system (ISMS).",
      "reference_url": "https://example.com/iso27001",
      "moscow": "must",
      "controls": [
        {
          "control_code": "A.5.1",
          "name": "Policies for information security",
          "description": "Define and approve a set of information security policies.",
          "rationale": "Ensures consistent governance across the organization.",
          "moscow": "must"
        }
      ]
    }
  ]
}
```

Request body for import/validate wraps this object:

```json
{
  "pack_key": "iso27001:2022",
  "name": "ISO 27001:2022",
  "vendor": "iso",
  "version": "2022",
  "payload": { }
}
```

(`payload` is the document above, including the `standards` array.)

## Recommendations

- Use stable **`pack_key`** values (idempotent reject on re-import).
- Run **validate** before import in CI or admin workflows.
- For 1000+ controls, prefer fewer large standards or split packs; apply uses per-row inserts (batch optimization is backlog).
- Ship framework-specific pack files separately from the product repo; document `pack_key` in release notes.

## Related

- [Compliance overview](README.md)
- [Phase 7 operations](../operations/phase7-compliance-and-lifecycle-guards.md)
- [services/compliance/README.md](../../services/compliance/README.md)
