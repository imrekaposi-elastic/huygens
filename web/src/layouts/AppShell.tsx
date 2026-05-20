import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { isPlatformAdmin, getAccessToken } from "@/auth/token";
import { OrganizationSwitcher } from "@/components/OrganizationSwitcher";

const mainNav = [{ to: "/", label: "Dashboard" }] as const;

const adminNav = [
  { to: "/agent-technologies", label: "Agent tech" },
  { to: "/infrastructure", label: "Infrastructure" },
  { to: "/agents", label: "Agents" },
] as const;

const projectsNav = { to: "/projects", label: "Projects" } as const;

function navClass(active: boolean) {
  return `min-h-11 rounded-lg px-3 py-2 text-sm md:min-h-0 ${
    active ? "bg-slate-800 text-white" : "text-slate-400 hover:bg-slate-800/60"
  }`;
}

export function AppShell() {
  const { user, logout } = useAuth();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const showAgents = isPlatformAdmin(getAccessToken());

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="flex flex-col border-b border-slate-800 bg-slate-900 md:w-56 md:border-b-0 md:border-r">
        <div className="p-4 font-semibold text-emerald-400">Huygens</div>
        <nav className="flex flex-1 flex-col gap-1 overflow-x-auto px-2 pb-2 md:px-3 md:pb-4">
          {mainNav.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={navClass(pathname === item.to)}
            >
              {item.label}
            </Link>
          ))}
          {showAgents &&
            adminNav.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={navClass(pathname.startsWith(item.to))}
              >
                {item.label}
              </Link>
            ))}
          <div className="hidden flex-1 md:block" aria-hidden />
          <Link
            to={projectsNav.to}
            className={navClass(
              pathname === projectsNav.to || pathname.startsWith("/projects/"),
            )}
          >
            {projectsNav.label}
          </Link>
        </nav>
        <div className="hidden border-t border-slate-800 p-3 md:block">
          <p className="truncate text-xs text-slate-500">{user?.username}</p>
          <button
            type="button"
            onClick={() => {
              logout();
              window.location.href = "/login";
            }}
            className="mt-2 text-sm text-slate-400 hover:text-white"
          >
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex flex-wrap items-center gap-3 border-b border-slate-800 bg-slate-900/80 px-4 py-3">
          <OrganizationSwitcher />
          <button
            type="button"
            className="ml-auto min-h-11 text-sm text-slate-400 md:hidden"
            onClick={() => {
              logout();
              window.location.href = "/login";
            }}
          >
            Sign out
          </button>
        </header>
        <main className="flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
