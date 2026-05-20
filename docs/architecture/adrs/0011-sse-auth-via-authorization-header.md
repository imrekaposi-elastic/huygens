# ADR 0011: SSE authentication via Authorization header

## Status

Accepted (Phase 5)

## Context

The web console needs server-push inventory updates (SSE). Browser **native `EventSource` cannot set custom headers**, which pushes teams toward passing JWTs as `?token=` query parameters. That leaks credentials in URLs, proxy logs, and browser history.

## Decision

1. **Inventory SSE** (`GET /api/v1/inventory/events/stream`) accepts JWT **only** via `Authorization: Bearer <token>`.
2. **Reject** query-parameter auth: `token`, `access_token`, `jwt`, `bearer` → HTTP **400** with a clear message.
3. **Console client** must use **`fetch()` streaming** (e.g. `@microsoft/fetch-event-source`) or equivalent — **not** `new EventSource(url)`.
4. **OIDC post-login redirect** (`OIDC_POST_LOGIN_REDIRECT` + `redirect=true` on IAM callback) puts the access token in the URL **fragment** (`#access_token=…`), **never** `?access_token=` (query strings are logged by servers and proxies).
5. **Production** serves SPA and APIs from one origin (nginx) so cookies or Bearer on fetch remain simple.

## Consequences

- Slightly more client code than native EventSource; correct security trade-off.
- SSE fan-out remains Kafka → broadcast consumer → in-process hub per inventory pod (ADR 0004).
