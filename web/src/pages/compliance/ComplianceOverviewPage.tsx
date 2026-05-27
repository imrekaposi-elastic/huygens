import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";

export function ComplianceOverviewPage() {
  const { selectedOrgId } = useAuth();
  const organizationId = selectedOrgId ?? "";

  const projects = useQuery({
    queryKey: ["projects", organizationId],
    queryFn: () => api.projects(organizationId),
    enabled: !!organizationId,
  });

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <h2 className="mb-1 text-sm font-medium text-slate-700 dark:text-slate-300">
        Link standards to resources
      </h2>
      <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">
        Open a project and use the <strong>Compliance</strong> tab, or assign per VM/network from
        the Virtual machines / Networks tabs (requires <strong>compliance_engineer</strong> or{" "}
        <strong>admin</strong>).
      </p>
      <ul className="flex flex-wrap gap-2">
        {(projects.data ?? []).map((p) => (
          <li key={p.id}>
            <Link
              to="/projects/$projectId/compliance"
              params={{ projectId: p.id }}
              className="rounded-lg border border-emerald-600/40 px-3 py-1.5 text-sm text-emerald-800 hover:bg-emerald-50 dark:text-emerald-200 dark:hover:bg-emerald-950/40"
            >
              {p.name}
            </Link>
          </li>
        ))}
        {!projects.data?.length && (
          <li className="text-sm text-slate-500">No projects in this organization yet.</li>
        )}
      </ul>
    </section>
  );
}
