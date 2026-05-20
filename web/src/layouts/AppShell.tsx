import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { isPlatformAdmin, getAccessToken } from "@/auth/token";

const nav = [
  { to: "/", label: "Dashboard" },
  { to: "/projects", label: "Projects" },
] as const;

export function AppShell() {
  const { user, organizations, selectedOrgId, setSelectedOrgId, logout } = useAuth();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const showAgents = isPlatformAdmin(getAccessToken());

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="border-b border-slate-800 bg-slate-900 md:w-56 md:border-b-0 md:border-r">
        <div className="p-4 font-semibold text-emerald-400">Huygens</div>
        <nav className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-col md:px-3 md:pb-4">
          {nav.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={`min-h-11 rounded-lg px-3 py-2 text-sm md:min-h-0 ${
                pathname === item.to || (item.to !== "/" && pathname.startsWith(item.to))
                  ? "bg-slate-800 text-white"
                  : "text-slate-400 hover:bg-slate-800/60"
              }`}
            >
              {item.label}
            </Link>
          ))}
          {showAgents && (
            <Link
              to="/agents"
              className={`min-h-11 rounded-lg px-3 py-2 text-sm ${
                pathname.startsWith("/agents") ? "bg-slate-800 text-white" : "text-slate-400"
              }`}
            >
              Agents
            </Link>
          )}
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
          <label className="text-sm text-slate-400">
            Organization
            <select
              className="ml-2 min-h-11 rounded border border-slate-700 bg-slate-800 px-2 text-sm text-white"
              value={selectedOrgId ?? ""}
              onChange={(e) => setSelectedOrgId(e.target.value)}
            >
              {organizations.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          </label>
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
