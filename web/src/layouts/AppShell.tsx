import { Outlet, useRouterState } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { canAccessAdmin, canAccessIpam, canAccessTopology } from "@/auth/permissions";
import { isPlatformAdmin, getAccessToken } from "@/auth/token";
import { OrganizationSwitcher } from "@/components/OrganizationSwitcher";
import { NavItem } from "@/components/NavItem";
import {
  AgentTechIcon,
  CloudIcon,
  FolderIcon,
  HomeIcon,
  NetworkIcon,
  ShieldIcon,
} from "@/components/icons/NavIcons";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useInventoryEvents } from "@/hooks/useInventoryEvents";

export function AppShell() {
  const { user, logout, selectedOrgId } = useAuth();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const token = getAccessToken();
  const showAgents = isPlatformAdmin(token);
  const showIpam = canAccessIpam(user, selectedOrgId, showAgents);
  const showTopology = canAccessTopology(user, selectedOrgId, showAgents);
  const showAdmin = canAccessAdmin(user, selectedOrgId, showAgents);

  useInventoryEvents(selectedOrgId, !!selectedOrgId);

  return (
    <div className="flex min-h-screen flex-col bg-slate-100 dark:bg-slate-950 md:flex-row">
      <aside className="flex flex-col border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900 md:w-56 md:border-b-0 md:border-r">
        <div className="p-4 font-semibold text-emerald-600 dark:text-emerald-400">Huygens</div>
        <nav className="flex flex-1 flex-col gap-1 overflow-x-auto px-2 pb-2 md:px-3 md:pb-4">
          <NavItem
            to="/"
            label="Home"
            icon={<HomeIcon />}
            active={pathname === "/"}
          />
          {showAgents && (
            <>
              <NavItem
                to="/agent-technologies"
                label="Fabric"
                icon={<AgentTechIcon />}
                active={pathname.startsWith("/agent-technologies")}
              />
              <NavItem
                to="/infrastructure"
                label="Infrastructure"
                icon={<CloudIcon />}
                active={pathname.startsWith("/infrastructure")}
              />
              <NavItem
                to="/agents"
                label="Agents"
                active={pathname.startsWith("/agents")}
                icon={
                  <svg
                    className="size-5 shrink-0"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.75"
                    aria-hidden
                  >
                    <rect x="4" y="4" width="16" height="6" rx="1" />
                    <rect x="4" y="14" width="16" height="6" rx="1" />
                    <circle cx="8" cy="7" r="0.75" fill="currentColor" stroke="none" />
                    <circle cx="8" cy="17" r="0.75" fill="currentColor" stroke="none" />
                  </svg>
                }
              />
            </>
          )}
          {showIpam && (
            <NavItem
              to="/ipam"
              label="IPAM"
              icon={<NetworkIcon />}
              active={pathname.startsWith("/ipam")}
            />
          )}
          {showTopology && (
            <NavItem
              to="/topology"
              label="Topology"
              icon={<NetworkIcon />}
              active={pathname.startsWith("/topology")}
            />
          )}
          {showAdmin && (
            <NavItem
              to="/admin/users"
              label="Admin"
              icon={<ShieldIcon />}
              active={pathname.startsWith("/admin")}
            />
          )}
          <div className="hidden flex-1 md:block" aria-hidden />
          <NavItem
            to="/projects"
            label="Projects"
            icon={<FolderIcon />}
            active={pathname === "/projects" || pathname.startsWith("/projects/")}
          />
        </nav>
        <div className="hidden border-t border-slate-200 p-3 dark:border-slate-800 md:block">
          <ThemeToggle className="mb-3 w-full justify-center" />
          <p className="truncate text-xs text-slate-500 dark:text-slate-500">{user?.username}</p>
          <button
            type="button"
            onClick={() => {
              logout();
              window.location.href = "/login";
            }}
            className="mt-2 text-sm text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-900 dark:text-white"
          >
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex flex-wrap items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-3 dark:border-slate-800 dark:bg-slate-900/80">
          <OrganizationSwitcher />
          <ThemeToggle className="hidden md:inline-flex" />
          <button
            type="button"
            className="min-h-11 text-sm text-slate-600 dark:text-slate-400 md:ml-auto md:hidden"
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
