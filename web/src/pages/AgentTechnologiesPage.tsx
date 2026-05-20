import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import { AgentTechIcon, PageTitle } from "@/components/icons/NavIcons";

export function AgentTechnologiesPage() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ["agent-technologies"],
    queryFn: () => api.agentTechnologies(),
  });

  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.updateAgentTechnology(id, { platform_enabled: enabled }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["agent-technologies"] }),
  });

  if (isLoading) return <p className="text-slate-600 dark:text-slate-400">Loading…</p>;
  if (error) return <p className="text-red-600 dark:text-red-400">{(error as Error).message}</p>;

  return (
    <div className="space-y-6">
      <div>
        <PageTitle icon={<AgentTechIcon />}>Fabric</PageTitle>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Fabric implementations that collect inventory (how agents talk to hypervisors). Disable
          platform-wide to block new enrollments. Per-project enablement is on each project page.
        </p>
      </div>
      <ul className="space-y-3">
        {data?.map((tech) => (
          <li
            key={tech.id}
            className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5"
          >
            <div>
              <p className="font-medium text-slate-900 dark:text-white">{tech.name}</p>
              <p className="font-mono text-sm text-slate-500 dark:text-slate-500">{tech.slug}</p>
              {tech.description && (
                <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{tech.description}</p>
              )}
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={tech.platform_enabled}
                disabled={toggle.isPending}
                onChange={(e) =>
                  toggle.mutate({ id: tech.id, enabled: e.target.checked }, {
                    onError: (err) =>
                      alert(err instanceof ApiError ? err.message : "Update failed"),
                  })
                }
              />
              Platform enabled
            </label>
          </li>
        ))}
      </ul>
    </div>
  );
}
