import { useEffect } from "react";
import { Link, Outlet, useRouterState } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import {
  CdIcon,
  CogIcon,
  FolderOpenIcon,
  NetworkIcon,
  PageTitleIcon,
  CheckmarkIcon,
  UsersIcon,
  VmIcon,
} from "@/components/icons/NavIcons";
import { useAuth } from "@/auth/AuthContext";
import { canAccessCompliance } from "@/auth/permissions";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import { useProjectWorkspace } from "@/pages/project/projectContext";

const subNavBase = [
  { tab: "vms" as const, label: "Virtual machines", icon: <VmIcon /> },
  { tab: "images" as const, label: "Images", icon: <CdIcon /> },
  { tab: "networks" as const, label: "Networks", icon: <NetworkIcon /> },
  { tab: "cloud-init" as const, label: "Cloud-init", icon: <CogIcon /> },
  { tab: "access" as const, label: "Access", icon: <UsersIcon /> },
];

type Props = { projectId: string };

export function ProjectLayout({ projectId }: Props) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { user, selectedOrgId } = useAuth();
  const platformAdmin = isPlatformAdmin(getAccessToken());
  const { agentId, setAgentId } = useProjectWorkspace();
  const qc = useQueryClient();

  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });

  const agentTechs = useQuery({
    queryKey: ["project-agent-technologies", projectId],
    queryFn: () => api.projectAgentTechnologies(projectId),
  });

  const agents = useQuery({
    queryKey: ["project-agents", projectId],
    queryFn: () => api.projectAgents(projectId),
  });

  useEffect(() => {
    if (!agentId && agents.data?.length) {
      setAgentId(agents.data[0].id);
    }
  }, [agentId, agents.data, setAgentId]);

  const organizationId = project.data?.organization_id ?? selectedOrgId ?? "";
  const showCompliance = canAccessCompliance(user, organizationId, platformAdmin);
  const subNav = showCompliance
    ? [
        ...subNavBase.slice(0, 3),
        { tab: "compliance" as const, label: "Compliance", icon: <CheckmarkIcon className="size-5" /> },
        ...subNavBase.slice(3),
      ]
    : subNavBase;

  const saveTechs = useMutation({
    mutationFn: (technologies: { agent_technology_id: string; enabled: boolean }[]) =>
      api.setProjectAgentTechnologies(projectId, technologies),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["project-agent-technologies", projectId] });
      void qc.invalidateQueries({ queryKey: ["project-agents", projectId] });
    },
  });

  return (
    <div className="flex flex-col gap-6 lg:flex-row">
      <nav className="flex shrink-0 flex-row gap-1 overflow-x-auto lg:w-48 lg:flex-col lg:gap-0.5">
        {subNav.map((item) => {
          const active = pathname.includes(`/projects/${projectId}/${item.tab}`);
          return (
            <Link
              key={item.tab}
              to={`/projects/$projectId/${item.tab}`}
              params={{ projectId }}
              className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2.5 text-sm lg:whitespace-normal ${
                active
                  ? "bg-slate-50 dark:bg-slate-800 font-medium text-slate-900 dark:text-white"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:bg-slate-800/60 hover:text-slate-800 dark:hover:text-slate-800 dark:text-slate-200"
              }`}
            >
              <span className={active ? "text-emerald-600 dark:text-emerald-400" : "text-slate-500 dark:text-slate-500"}>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="min-w-0 flex-1 space-y-6">
        <div>
          <Link to="/projects" className="text-sm text-emerald-600 dark:text-emerald-400 hover:underline">
            ← Projects
          </Link>
          <h1 className="mt-2 flex items-center gap-2 text-2xl font-semibold">
            <PageTitleIcon>
              <FolderOpenIcon className="text-amber-700 dark:text-amber-400/90" />
            </PageTitleIcon>
            {project.data?.name ?? "Project"}
          </h1>
          {project.data?.description && (
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-500">{project.data.description}</p>
          )}
        </div>

        <section className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/80 p-4">
          <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">Agent workspace</h2>
          <div className="mt-3 grid gap-4 md:grid-cols-2">
            <label className="block text-sm">
              Agent
              <select
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                value={agentId}
                onChange={(e) => setAgentId(e.target.value)}
              >
                <option value="">Select agent…</option>
                {agents.data?.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} ({a.connection_status})
                  </option>
                ))}
              </select>
            </label>
            <div className="text-sm">
              <p className="text-slate-600 dark:text-slate-400">Fabric</p>
              <ul className="mt-2 max-h-32 space-y-1 overflow-y-auto">
                {agentTechs.data?.map((tech) => (
                  <li key={tech.agent_technology_id} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={tech.enabled}
                      disabled={!tech.platform_enabled || saveTechs.isPending}
                      onChange={(e) => {
                        const next = (agentTechs.data ?? []).map((t) => ({
                          agent_technology_id: t.agent_technology_id,
                          enabled:
                            t.agent_technology_id === tech.agent_technology_id
                              ? e.target.checked
                              : t.enabled,
                        }));
                        saveTechs.mutate(next);
                      }}
                    />
                    <span className={tech.platform_enabled ? "text-slate-700 dark:text-slate-300" : "text-slate-600"}>
                      {tech.name}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          {saveTechs.isError && (
            <p className="mt-2 text-xs text-red-700 dark:text-red-300">
              {saveTechs.error instanceof ApiError ? saveTechs.error.message : "Save failed"}
            </p>
          )}
        </section>

        <Outlet />
      </div>
    </div>
  );
}
