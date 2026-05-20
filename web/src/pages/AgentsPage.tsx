import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthContext";
import { AgentEditDialog } from "@/components/AgentEditDialog";
import { AgentMetricsPanel } from "@/components/AgentMetricsPanel";
import { AgentRegisterDialog } from "@/components/AgentRegisterDialog";
import { api, ApiError } from "@/api/client";
import type { AgentOut } from "@/api/types";

function regionLabel(agent: AgentOut): string {
  if (!agent.region_id) return "— unassigned";
  if (agent.region_name) {
    return agent.region_slug ? `${agent.region_name} (${agent.region_slug})` : agent.region_name;
  }
  return agent.region_id.slice(0, 8) + "…";
}

function agentHealthStatus(agent: AgentOut): {
  label: string;
  className: string;
  title?: string;
} {
  if (agent.last_poll_error) {
    return {
      label: agent.last_poll_error,
      className: "text-amber-800 dark:text-amber-300",
      title: agent.last_poll_error,
    };
  }
  if (agent.connection_status === "connected") {
    return { label: "healthy", className: "text-emerald-600 dark:text-emerald-400" };
  }
  if (agent.connection_status === "error") {
    return { label: "unhealthy", className: "text-red-600 dark:text-red-400" };
  }
  return {
    label: agent.connection_status,
    className: "text-slate-600 dark:text-slate-400",
  };
}

export function AgentsPage() {
  const { selectedOrgId, organizations } = useAuth();
  const qc = useQueryClient();
  const [registerOpen, setRegisterOpen] = useState(false);
  const [editAgent, setEditAgent] = useState<AgentOut | null>(null);
  const [metricsAgent, setMetricsAgent] = useState<AgentOut | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const orgId = selectedOrgId ?? organizations[0]?.id;

  const { data, isLoading, error } = useQuery({
    queryKey: ["registry-agents"],
    queryFn: () => api.registryAgents(),
  });

  const agents = data?.filter((a) => !orgId || a.organization_id === orgId) ?? data;

  const invalidate = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["registry-agents"] }),
      qc.invalidateQueries({ queryKey: ["dashboard"] }),
      qc.invalidateQueries({ queryKey: ["infrastructure-providers"] }),
    ]);
  };

  async function handleDelete(agentId: string, agentName: string) {
    if (
      !window.confirm(
        `Delete agent "${agentName}" from the registry and remove its inventory snapshot?`,
      )
    ) {
      return;
    }
    setErr(null);
    setDeletingId(agentId);
    try {
      await api.deleteAgent(agentId);
      invalidate();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  if (isLoading) return <p className="text-slate-600 dark:text-slate-400">Loading…</p>;
  if (error) return <p className="text-red-600 dark:text-red-400">{(error as Error).message}</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Agents</h1>
          <p className="text-sm text-slate-500 dark:text-slate-500">
            Platform admin — one region per libvirt agent; use Edit to change URL, region, or TLS.
          </p>
        </div>
        <button
          type="button"
          disabled={!orgId}
          onClick={() => setRegisterOpen(true)}
          className="min-h-11 rounded-lg bg-emerald-600 px-4 font-medium hover:bg-emerald-500 disabled:opacity-50"
        >
          Register agent
        </button>
      </div>
      {!orgId && (
        <p className="text-sm text-amber-800 dark:text-amber-300">Select an organization in the header to register an agent.</p>
      )}
      {ok && <p className="text-sm text-emerald-600 dark:text-emerald-400">{ok}</p>}
      {err && <p className="text-sm text-red-600 dark:text-red-400">{err}</p>}
      {metricsAgent && (
        <AgentMetricsPanel agent={metricsAgent} onClose={() => setMetricsAgent(null)} />
      )}
      <div className="space-y-2 md:hidden">
        {agents?.map((a) => {
          const health = agentHealthStatus(a);
          return (
          <div
            key={a.id}
            className="flex items-start justify-between gap-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3"
          >
            <div className="min-w-0">
              <p className="font-medium">{a.name}</p>
              <p className="text-xs text-slate-500 dark:text-slate-500">{regionLabel(a)}</p>
              <p className="text-sm text-slate-600 dark:text-slate-400">{a.connection_status}</p>
              <p className={`text-xs font-medium ${health.className}`} title={health.title}>
                {health.label}
              </p>
            </div>
            <AgentActions
              deletingId={deletingId}
              agentId={a.id}
              onEdit={() => setEditAgent(a)}
              onMetrics={() => setMetricsAgent(a)}
              onDelete={() => void handleDelete(a.id, a.name)}
            />
          </div>
          );
        })}
      </div>
      <table className="hidden w-full text-sm md:table">
        <thead className="text-slate-500 dark:text-slate-500">
          <tr>
            <th className="pb-2 text-left">Name</th>
            <th className="pb-2 text-left">Region</th>
            <th className="pb-2 text-left">Connection</th>
            <th className="pb-2 text-left">Status</th>
            <th className="pb-2 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {agents?.map((a) => {
            const health = agentHealthStatus(a);
            return (
            <tr key={a.id} className="border-t border-slate-200 dark:border-slate-800">
              <td className="py-2">{a.name}</td>
              <td className="py-2 text-slate-600 dark:text-slate-400">{regionLabel(a)}</td>
              <td className="text-slate-600 dark:text-slate-400">{a.connection_status}</td>
              <td
                className={`max-w-xs truncate text-xs font-medium ${health.className}`}
                title={health.title}
              >
                {health.label}
              </td>
              <td className="py-2 text-right">
                <AgentActions
                  deletingId={deletingId}
                  agentId={a.id}
                  onEdit={() => setEditAgent(a)}
                  onMetrics={() => setMetricsAgent(a)}
                  onDelete={() => void handleDelete(a.id, a.name)}
                  inline
                />
              </td>
            </tr>
            );
          })}
        </tbody>
      </table>
      {orgId && (
        <AgentRegisterDialog
          open={registerOpen}
          organizationId={orgId}
          onClose={() => setRegisterOpen(false)}
          onRegistered={invalidate}
        />
      )}
      <AgentEditDialog
        open={editAgent !== null}
        agent={editAgent}
        onClose={() => setEditAgent(null)}
        onSaved={async (message) => {
          await invalidate();
          setOk(message);
        }}
      />
    </div>
  );
}

function AgentActions({
  agentId,
  deletingId,
  onEdit,
  onMetrics,
  onDelete,
  inline,
}: {
  agentId: string;
  deletingId: string | null;
  onEdit: () => void;
  onMetrics: () => void;
  onDelete: () => void;
  inline?: boolean;
}) {
  const btn = inline
    ? "rounded border border-slate-300 dark:border-slate-600 px-2 py-1 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
    : "text-sm text-slate-700 dark:text-slate-300";
  const delBtn = inline
    ? "rounded border border-red-300 dark:border-red-900/80 px-2 py-1 text-red-700 dark:text-red-300 hover:bg-red-50 dark:hover:bg-red-950/40 disabled:opacity-50"
    : "text-sm text-red-700 dark:text-red-300";

  const buttons = (
    <>
      <button type="button" onClick={onEdit} className={btn}>
        Edit
      </button>
      <button type="button" onClick={onMetrics} className={btn}>
        Metrics
      </button>
      <button
        type="button"
        onClick={onDelete}
        disabled={deletingId === agentId}
        className={delBtn}
      >
        {deletingId === agentId ? "Deleting…" : "Delete"}
      </button>
    </>
  );

  if (inline) {
    return <span className="inline-flex flex-wrap justify-end gap-1">{buttons}</span>;
  }
  return <div className="flex shrink-0 flex-col gap-1">{buttons}</div>;
}
