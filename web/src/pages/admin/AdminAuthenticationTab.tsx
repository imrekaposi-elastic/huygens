import { useState } from "react";
import { useAuth } from "@/auth/AuthContext";
import { api, ApiError } from "@/api/client";

export function AdminAuthenticationTab() {
  const { selectedOrgId, organizations } = useAuth();
  const [oidcBusy, setOidcBusy] = useState(false);
  const [oidcErr, setOidcErr] = useState<string | null>(null);
  const org = organizations.find((o) => o.id === selectedOrgId);

  async function testOidcAuthorize() {
    if (!selectedOrgId) return;
    setOidcErr(null);
    setOidcBusy(true);
    try {
      const { authorization_url } = await api.oidcAuthorizeUrl(selectedOrgId);
      window.open(authorization_url, "_blank", "noopener,noreferrer");
    } catch (e) {
      setOidcErr(
        e instanceof ApiError
          ? e.message
          : "OIDC is not enabled or Keycloak is unreachable. Enable OIDC_ENABLED on IAM.",
      );
    } finally {
      setOidcBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/80 p-4">
        <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">Local authentication</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          Username and password login against the IAM service database. API keys are issued per
          user from <span className="font-mono text-slate-700 dark:text-slate-300">POST /api/v1/auth/api-keys</span>{" "}
          (CLI / automation; not yet exposed in this console).
        </p>
        <ul className="mt-3 list-inside list-disc text-sm text-slate-500 dark:text-slate-500">
          <li>Default bootstrap user: platform-admin (setup wizard)</li>
          <li>Organization users are created under Admin → Users & roles</li>
        </ul>
      </section>

      <section className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/80 p-4">
        <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">OIDC / Keycloak (SSO backend)</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          When <span className="font-mono text-slate-700 dark:text-slate-300">OIDC_ENABLED=true</span> on IAM, users
          authenticate via Keycloak. Group claims are mapped to Huygens roles using IdP group
          mappings (organization-scoped and platform-scoped).
        </p>
        <dl className="mt-4 grid gap-2 text-sm md:grid-cols-2">
          <div>
            <dt className="text-slate-500 dark:text-slate-500">Authorize endpoint</dt>
            <dd className="font-mono text-xs text-slate-700 dark:text-slate-300">GET /api/v1/auth/oidc/authorize</dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-500">Callback</dt>
            <dd className="font-mono text-xs text-slate-700 dark:text-slate-300">GET /api/v1/auth/oidc/callback</dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-500">SPA callback</dt>
            <dd className="font-mono text-xs text-slate-700 dark:text-slate-300">/auth/callback (#access_token=…)</dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-500">Docker profile</dt>
            <dd className="font-mono text-xs text-slate-700 dark:text-slate-300">docker compose --profile sso up</dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-500">
          Configure issuer, client id/secret, and post-login redirect via IAM environment variables
          (see <span className="font-mono">compose.env.example</span>).
        </p>
        {selectedOrgId && org && (
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={oidcBusy}
              onClick={() => void testOidcAuthorize()}
              className="min-h-11 rounded-lg border border-slate-300 dark:border-slate-600 px-4 text-sm hover:bg-slate-50 dark:bg-slate-800 disabled:opacity-50"
            >
              {oidcBusy ? "Opening…" : `Test OIDC login for ${org.name}`}
            </button>
            <span className="text-xs text-slate-500 dark:text-slate-500">
              Opens Keycloak authorize URL in a new tab (requires OIDC enabled).
            </span>
          </div>
        )}
        {oidcErr && <p className="mt-2 text-sm text-amber-700 dark:text-amber-400">{oidcErr}</p>}
      </section>

      <section className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/80 p-4">
        <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">Planned backends (not in console yet)</h2>
        <ul className="mt-2 list-inside list-disc text-sm text-slate-500 dark:text-slate-500">
          <li>LDAP / Active Directory — via Keycloak user federation</li>
          <li>SAML — via Keycloak identity brokering</li>
          <li>Per-organization IdP selection — Phase 2+</li>
        </ul>
      </section>
    </div>
  );
}
