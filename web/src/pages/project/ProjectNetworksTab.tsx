import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import { NetworkIcon } from "@/components/icons/NavIcons";
import { liveQueryOptions } from "@/lib/liveRefresh";
import { filterManagedNetworks, LIBVIRT_SYSTEM_NETWORK } from "@/lib/systemNetwork";
import { useProjectWorkspace } from "@/pages/project/projectContext";
import { ResourceList, ResourceListEmpty, ResourceListItem } from "@/pages/project/ResourceList";
import { NetworkDialog } from "@/pages/project/NetworkDialog";

type Props = { projectId: string };

export function ProjectNetworksTab({ projectId }: Props) {
  const { agentId } = useProjectWorkspace();
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<"create" | { edit: Record<string, unknown> } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["networks", projectId, agentId],
    queryFn: () => api.listNetworks(projectId, agentId),
    enabled: !!agentId,
    ...liveQueryOptions,
  });

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ["networks", projectId, agentId] });
    void qc.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const remove = useMutation({
    mutationFn: (name: string) => api.deleteNetwork(projectId, agentId, name),
    onSuccess: invalidate,
  });

  const unassign = useMutation({
    mutationFn: (name: string) =>
      api.unassignResourceFromProject(projectId, agentId, "network", name),
    onSuccess: invalidate,
  });

  if (!agentId) {
    return <p className="text-slate-500 dark:text-slate-500">Select an agent in the project header to manage networks.</p>;
  }

  const networks = filterManagedNetworks(
    (data ?? []) as { name: string | null; readonly?: boolean; active?: boolean; bridge?: string; ipv4_cidr?: string }[],
  );

  return (
    <>
      <p className="text-sm text-slate-500 dark:text-slate-500">
        Operator-managed virtual networks. The system network{" "}
        <span className="font-mono text-slate-600 dark:text-slate-400">{LIBVIRT_SYSTEM_NETWORK}</span> is provided by
        libvirt and is not listed or assignable.
      </p>
      <ResourceList
        title="Virtual networks"
        titleIcon={<NetworkIcon />}
        onNew={() => setDialog("create")}
        loading={isLoading}
      >
        {networks.length === 0 && !isLoading ? (
          <ResourceListEmpty message="No operator-managed networks on this agent." />
        ) : (
          networks.map((net) => {
            const name = String(net.name ?? "");
            const readonly = Boolean(net.readonly);
            const subtitle = [
              net.active === false ? "inactive" : "active",
              net.bridge ? `bridge ${net.bridge}` : null,
              net.ipv4_cidr ? String(net.ipv4_cidr) : null,
            ]
              .filter(Boolean)
              .join(" · ");
            return (
              <ResourceListItem
                key={name}
                name={name}
                subtitle={subtitle}
                onEdit={() => setDialog({ edit: net })}
                onDelete={
                  readonly
                    ? undefined
                    : () => {
                        if (window.confirm(`Delete network "${name}" on the agent?`))
                          remove.mutate(name);
                      }
                }
                deleteLabel="Delete on agent"
                extra={
                  <>
                    {readonly && (
                      <span className="mt-1 inline-block rounded bg-slate-50 dark:bg-slate-800 px-2 text-xs text-slate-600 dark:text-slate-400">
                        readonly
                      </span>
                    )}
                    <button
                      type="button"
                      className="mt-1 block text-xs text-slate-600 dark:text-slate-400 underline"
                      onClick={() => unassign.mutate(name)}
                    >
                      Unassign from project
                    </button>
                  </>
                }
              />
            );
          })
        )}
      </ResourceList>

      <NetworkDialog
        open={dialog !== null}
        mode={dialog === "create" ? "create" : "edit"}
        projectId={projectId}
        agentId={agentId}
        initial={dialog && dialog !== "create" ? dialog.edit : null}
        onClose={() => setDialog(null)}
        onSaved={invalidate}
      />
      {remove.isError && (
        <p className="text-sm text-red-700 dark:text-red-300">
          {remove.error instanceof ApiError ? remove.error.message : "Delete failed"}
        </p>
      )}
    </>
  );
}
