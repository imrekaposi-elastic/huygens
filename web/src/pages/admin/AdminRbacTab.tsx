import { ROLE_CATALOG, ORG_ROLES, PLATFORM_ROLES, PROJECT_ROLES } from "@/lib/rbac";

export function AdminRbacTab() {
  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/80 p-4">
        <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">Role namespaces</h2>
        <dl className="mt-3 space-y-3 text-sm">
          <div>
            <dt className="font-mono text-emerald-600/90 dark:text-emerald-400/90">platform</dt>
            <dd className="text-slate-600 dark:text-slate-400">{PLATFORM_ROLES.join(", ")}</dd>
          </div>
          <div>
            <dt className="font-mono text-emerald-600/90 dark:text-emerald-400/90">organization</dt>
            <dd className="text-slate-600 dark:text-slate-400">{ORG_ROLES.join(", ")}</dd>
          </div>
          <div>
            <dt className="font-mono text-emerald-600/90 dark:text-emerald-400/90">project</dt>
            <dd className="text-slate-600 dark:text-slate-400">{PROJECT_ROLES.join(", ")}</dd>
          </div>
        </dl>
      </section>

      <section className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/80 p-4">
        <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">Built-in roles and permissions</h2>
        <table className="mt-3 w-full min-w-[32rem] text-left text-sm">
          <thead>
            <tr className="border-b border-slate-300 dark:border-slate-700 text-slate-500 dark:text-slate-500">
              <th className="py-2 pr-4">Scope</th>
              <th className="py-2 pr-4">Role</th>
              <th className="py-2">Permissions</th>
            </tr>
          </thead>
          <tbody>
            {ROLE_CATALOG.map((row) => (
              <tr key={`${row.scope}-${row.role}`} className="border-b border-slate-200 dark:border-slate-800/80">
                <td className="py-2 pr-4 font-mono text-xs text-slate-600 dark:text-slate-400">{row.scope}</td>
                <td className="py-2 pr-4 font-mono text-xs text-emerald-600/90 dark:text-emerald-400/90">{row.role}</td>
                <td className="py-2 font-mono text-xs text-slate-600 dark:text-slate-400">
                  {row.permissions.join(", ")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-500">
          Additional project roles (ssh_access, security_engineer, compliance_engineer) follow the
          same permission model in IAM; assign them via project role API.
        </p>
      </section>
    </div>
  );
}
