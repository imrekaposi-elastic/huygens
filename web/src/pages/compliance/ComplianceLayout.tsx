import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { ComplianceMembershipLegend } from "@/components/compliance/ComplianceMembershipLegend";
import { PageTitle, CheckmarkIcon } from "@/components/icons/NavIcons";

type Props = { organizationId: string };

const TABS = [
  { to: "/compliance/overview" as const, label: "Overview" },
  { to: "/compliance/explorer" as const, label: "Explorer" },
  { to: "/compliance/catalog" as const, label: "Catalog" },
  { to: "/compliance/checks" as const, label: "Checks" },
] as const;

export function ComplianceLayout({ organizationId }: Props) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const onOverview =
    pathname === "/compliance" ||
    pathname === "/compliance/" ||
    pathname === "/compliance/overview";

  const dashboard = useQuery({
    queryKey: ["compliance-dashboard", organizationId],
    queryFn: () => api.complianceDashboard(organizationId),
    enabled: onOverview && !!organizationId,
  });

  const dash = dashboard.data;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <PageTitle icon={<CheckmarkIcon />}>Compliance</PageTitle>

      <nav className="flex flex-wrap gap-2 border-b border-slate-200 pb-2 dark:border-slate-800">
        {TABS.map((tab) => {
          const active = pathname === tab.to || pathname.startsWith(`${tab.to}/`);
          return (
            <Link
              key={tab.to}
              to={tab.to}
              className={`rounded-lg px-3 py-2 text-sm font-medium ${
                active
                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-200"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>

      <ComplianceMembershipLegend className="-mt-2 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2 dark:border-slate-800 dark:bg-slate-900/50" />

      {onOverview && (
        <>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Organization compliance at a glance. Use <strong>Explorer</strong> to find coverage gaps,
            <strong> Catalog</strong> to define standards, and <strong>Checks</strong> for review
            cycles. Link standards to workloads under <strong>Projects</strong> or{" "}
            <strong>Infrastructure</strong> for provider/region inheritance.
          </p>
          {dashboard.isLoading && (
            <p className="text-sm text-slate-500">Loading dashboard…</p>
          )}
          {dash && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ["Catalog items", dash.catalog_count],
                ["Active checks", dash.checks_active],
                ["Expiring (30d)", dash.checks_expiring_soon],
                ["Criticality assignments", dash.assignments_count],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
                >
                  <p className="text-xs text-slate-500">{label}</p>
                  <p className="text-2xl font-semibold text-emerald-700 dark:text-emerald-300">
                    {value}
                  </p>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      <Outlet />
    </div>
  );
}
