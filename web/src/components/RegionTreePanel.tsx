import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import { InfrastructureCompliancePanel } from "@/components/compliance/InfrastructureCompliancePanel";
import { InfrastructureCharacteristicsPanel } from "@/components/compliance/InfrastructureCharacteristicsPanel";
import { GlobeIcon } from "@/components/icons/NavIcons";
import type { RegionTreeNode } from "@/api/types";

type Props = {
  nodes: RegionTreeNode[];
  infrastructureProviderId: string;
  organizationId?: string | null;
  depth?: number;
};

export function RegionTreePanel({
  nodes,
  infrastructureProviderId,
  organizationId = null,
  depth = 0,
}: Props) {
  const qc = useQueryClient();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const remove = useMutation({
    mutationFn: (regionId: string) => api.deleteRegion(infrastructureProviderId, regionId),
    onSuccess: () => {
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["infrastructure-provider", infrastructureProviderId] });
      void qc.invalidateQueries({ queryKey: ["infrastructure-providers"] });
      void qc.invalidateQueries({ queryKey: ["registry-agents"] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Delete failed"),
  });

  async function handleDelete(node: RegionTreeNode) {
    const agentNote =
      node.agents.length > 0 || node.descendant_agent_count > 0
        ? "\n\nAgents on this region (and sub-regions) will be unassigned from the region tree."
        : "";
    const childNote = node.children.length > 0 ? "\n\nSub-regions will also be removed." : "";
    if (
      !window.confirm(
        `Delete region "${node.name}"?${childNote}${agentNote}`,
      )
    ) {
      return;
    }
    setDeletingId(node.id);
    try {
      await remove.mutateAsync(node.id);
    } finally {
      setDeletingId(null);
    }
  }

  if (!nodes.length) {
    return <p className="text-sm text-slate-500 dark:text-slate-500">No regions yet.</p>;
  }

  return (
    <>
      {err && <p className="mb-2 text-sm text-red-600 dark:text-red-400">{err}</p>}
      <ul className={depth === 0 ? "space-y-2" : "ml-4 mt-2 space-y-2 border-l border-slate-300 dark:border-slate-700 pl-3"}>
        {nodes.map((node) => (
          <li key={node.id} className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/90 dark:bg-slate-900/50 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <GlobeIcon className="size-4 shrink-0 text-slate-500 dark:text-slate-500" />
              <span className="font-medium">{node.name}</span>
              <span className="font-mono text-xs text-slate-500 dark:text-slate-500">{node.slug}</span>
              {node.operational ? (
                <span className="rounded bg-emerald-950 px-2 py-0.5 text-xs text-emerald-700 dark:text-emerald-300">
                  operational
                </span>
              ) : (
                <span className="rounded bg-slate-50 dark:bg-slate-800 px-2 py-0.5 text-xs text-slate-600 dark:text-slate-400">
                  no agent coverage
                </span>
              )}
              {node.has_direct_agent && (
                <span className="text-xs text-slate-600 dark:text-slate-400">agent on this node</span>
              )}
              {node.descendant_agent_count > 0 && (
                <span className="text-xs text-slate-500 dark:text-slate-500">
                  {node.descendant_agent_count} agent(s) in subtree
                </span>
              )}
              <button
                type="button"
                disabled={deletingId === node.id || remove.isPending}
                onClick={() => void handleDelete(node)}
                className="ml-auto rounded border border-red-300 dark:border-red-900/80 px-2 py-1 text-xs text-red-700 dark:text-red-300 hover:bg-red-50 dark:bg-red-950/40 disabled:opacity-50"
              >
                {deletingId === node.id ? "Deleting…" : "Delete"}
              </button>
            </div>
            {node.agents.length > 0 && (
              <ul className="mt-2 space-y-1 text-sm text-slate-600 dark:text-slate-400">
                {node.agents.map((a) => (
                  <li key={a.id} className="font-mono text-xs">
                    {a.name} · {a.agent_technology_slug} · {a.connection_status}
                  </li>
                ))}
              </ul>
            )}
            {organizationId && (
              <>
                <InfrastructureCompliancePanel
                  organizationId={organizationId}
                  providerId={infrastructureProviderId}
                  regionId={node.id}
                />
                <InfrastructureCharacteristicsPanel
                  organizationId={organizationId}
                  providerId={infrastructureProviderId}
                  regionId={node.id}
                />
              </>
            )}
            {node.children.length > 0 && (
              <RegionTreePanel
                nodes={node.children}
                infrastructureProviderId={infrastructureProviderId}
                organizationId={organizationId}
                depth={depth + 1}
              />
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
