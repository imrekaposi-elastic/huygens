import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
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
  const [showAvailable, setShowAvailable] = useState(false);
  const [dialog, setDialog] = useState<"create" | { edit: Record<string, unknown> } | null>(null);

  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });
  const organizationId = project.data?.organization_id ?? "";

  const allocations = useQuery({
    queryKey: ["ipam-allocations", organizationId, projectId],
    queryFn: () => api.listProjectIpAllocations(organizationId, projectId),
    enabled: !!organizationId && !!projectId,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["networks", projectId, agentId],
    queryFn: () => api.listNetworks(projectId, agentId),
    enabled: !!agentId,
    ...liveQueryOptions,
  });

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ["networks", projectId, agentId] });
    void qc.invalidateQueries({ queryKey: ["ipam-allocations", organizationId, projectId] });
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
    return (
      <p className="text-slate-500 dark:text-slate-500">
        Select an agent in the project header to manage networks.
      </p>
    );
  }

  const networks = filterManagedNetworks(
    (data ?? []) as {
      name: string | null;
      readonly?: boolean;
      active?: boolean;
      bridge?: string;
      ipv4_cidr?: string;
    }[],
  );

  const availableBlocks = (allocations.data ?? []).filter((a) => a.status === "reserved");
  const inUseBlocks = (allocations.data ?? []).filter((a) => a.status === "allocated");

  return (
    <>
      <p className="text-sm text-slate-500 dark:text-slate-500">
        Deploy libvirt virtual networks on the selected agent. Subnet blocks come from{" "}
        <Link to="/ipam" className="font-medium text-emerald-600 dark:text-emerald-400 hover:underline">
          IPAM
        </Link>
        . The system network{" "}
        <span className="font-mono text-slate-600 dark:text-slate-400">{LIBVIRT_SYSTEM_NETWORK}</span> is not
        listed here.
      </p>

      <div className="space-y-2">
        <button
          type="button"
          onClick={() => setShowAvailable((v) => !v)}
          className="flex min-h-10 w-full items-center justify-between gap-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900/80 px-4 text-left text-sm font-medium text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800/80"
          aria-expanded={showAvailable}
        >
          <span>Available networks</span>
          <span className="flex items-center gap-2 text-xs font-normal text-slate-500 dark:text-slate-500">
            {allocations.isLoading ? (
              "…"
            ) : (
              <>
                {availableBlocks.length} ready
                {inUseBlocks.length > 0 ? ` · ${inUseBlocks.length} in use` : ""}
              </>
            )}
            <span className="text-slate-400" aria-hidden>
              {showAvailable ? "▾" : "▸"}
            </span>
          </span>
        </button>

        {showAvailable && (
          <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/50 px-4 py-3">
            {allocations.isLoading ? (
              <p className="text-sm text-slate-500 dark:text-slate-500">Loading…</p>
            ) : availableBlocks.length === 0 ? (
              <p className="text-sm text-slate-600 dark:text-slate-400">
                No subnet blocks ready to use. Assign blocks in{" "}
                <Link to="/ipam" className="text-emerald-600 dark:text-emerald-400 hover:underline">
                  IPAM
                </Link>
                , then create a virtual network below.
              </p>
            ) : (
              <>
                <p className="text-xs text-slate-500 dark:text-slate-500">
                  Reserved blocks — pick one when you click New virtual network.
                </p>
                <ul className="mt-2 divide-y divide-slate-200 dark:divide-slate-800 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-sm">
                  {availableBlocks.map((row) => (
                    <li
                      key={row.id}
                      className="flex items-center justify-between gap-2 px-3 py-2 font-mono text-slate-800 dark:text-slate-200"
                    >
                      {row.cidr}
                      <span className="text-xs font-sans text-emerald-700 dark:text-emerald-400">
                        available
                      </span>
                    </li>
                  ))}
                </ul>
              </>
            )}
            {inUseBlocks.length > 0 && (
              <p className="mt-3 text-xs text-slate-500 dark:text-slate-500">
                In use on agent:{" "}
                {inUseBlocks.map((b) => `${b.cidr}${b.network_name ? ` (${b.network_name})` : ""}`).join(", ")}
              </p>
            )}
          </div>
        )}
      </div>

      <ResourceList
        title="Virtual networks"
        titleIcon={<NetworkIcon />}
        onNew={() => setDialog("create")}
        loading={isLoading}
      >
        {networks.length === 0 && !isLoading ? (
          <ResourceListEmpty message="No virtual networks on this agent for this project." />
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
        organizationId={organizationId}
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
