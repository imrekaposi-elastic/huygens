import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { PageTitle, ShieldIcon } from "@/components/icons/NavIcons";
import { useAuth } from "@/auth/AuthContext";

const TABS = [
  { to: "/admin/users" as const, label: "Users & roles" },
  { to: "/admin/idp" as const, label: "IdP mappings" },
  { to: "/admin/authentication" as const, label: "Authentication" },
  { to: "/admin/rbac" as const, label: "RBAC reference" },
];

export function AdminLayout({ platformAdmin }: { platformAdmin: boolean }) {
  const { organizations, selectedOrgId } = useAuth();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const org = organizations.find((o) => o.id === selectedOrgId);

  return (
    <div className="space-y-6">
      <PageTitle icon={<ShieldIcon />}>Admin</PageTitle>
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Manage users, organization roles, IdP group → role mappings, and authentication backends
        {org ? (
          <>
            {" "}
            for <span className="text-slate-800 dark:text-slate-200">{org.name}</span>
          </>
        ) : (
          ""
        )}
        .
        {platformAdmin && (
          <span className="ml-1 text-emerald-600/90 dark:text-emerald-400/90">Platform administrator view.</span>
        )}
      </p>

      <nav className="flex flex-wrap gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
        {TABS.map((tab) => {
          const active = pathname === tab.to || pathname.startsWith(`${tab.to}/`);
          return (
            <Link
              key={tab.to}
              to={tab.to}
              className={`rounded-lg px-3 py-2 text-sm ${
                active
                  ? "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:bg-slate-800 hover:text-slate-900 dark:hover:text-slate-900 dark:text-white"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>

      <Outlet />
    </div>
  );
}
