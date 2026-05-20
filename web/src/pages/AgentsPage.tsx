import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthContext";
import { AgentMetricsPanel } from "@/components/AgentMetricsPanel";
import { AgentMigrateRegionDialog } from "@/components/AgentMigrateRegionDialog";
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

export function AgentsPage() {
  const { selectedOrgId, organizations } = useAuth();
  const qc = useQueryClient();
  const [registerOpen, setRegisterOpen] = useState(false);
  const [migrateAgent, setMigrateAgent] = useState<AgentOut | null>(null);
  const [metricsAgent, setMetricsAgent] = useState<AgentOut | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);

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

  async function handleToggleTls(agentId: string, current: boolean) {
    setErr(null);
    try {
      await api.patchAgent(agentId, { tls_verify: !current });
      invalidate();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Update failed");
    }
  }

  async function handleTestConnection(agentId: string) {
    setErr(null);
    setTestingId(agentId);
    try {
      await api.testAgentConnection(agentId);
      invalidate();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Connection test failed");
    } finally {
      setTestingId(null);
    }
  }

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
            Platform admin — one region per libvirt agent; move to relocate coverage in the tree.
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
        {agents?.map((a) => (
          <div
            key={a.id}
            className="flex items-start justify-between gap-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-3"
          >
            <div className="min-w-0">
              <p className="font-medium">{a.name}</p>
              <p className="text-xs text-slate-500 dark:text-slate-500">{regionLabel(a)}</p>
              <p className="truncate text-xs text-slate-500 dark:text-slate-500">{a.base_url}</p>
              <p className="text-sm">
                {a.connection_status}
                {a.tls_verify === false ? " · TLS verify off" : ""}
              </p>
              {a.last_poll_error && (
                <p className="text-xs text-amber-800 dark:text-amber-300">{a.last_poll_error}</p>
              )}
            </div>
            <AgentActions
              agent={a}
              testingId={testingId}
              deletingId={deletingId}
              onMetrics={() => setMetricsAgent(a)}
              onMigrate={() => setMigrateAgent(a)}
              onToggleTls={() => void handleToggleTls(a.id, a.tls_verify !== false)}
              onTest={() => void handleTestConnection(a.id)}
              onDelete={() => void handleDelete(a.id, a.name)}
            />
          </div>
        ))}
      </div>
      <table className="hidden w-full text-sm md:table">
        <thead className="text-slate-500 dark:text-slate-500">
          <tr>
            <th className="pb-2 text-left">Name</th>
            <th className="pb-2 text-left">Region</th>
            <th>Base URL</th>
            <th>Status</th>
            <th>Error</th>
            <th className="pb-2 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {agents?.map((a) => (
            <tr key={a.id} className="border-t border-slate-200 dark:border-slate-800">
              <td className="py-2">{a.name}</td>
              <td className="py-2 text-slate-600 dark:text-slate-400">{regionLabel(a)}</td>
              <td className="font-mono text-xs">{a.base_url}</td>
              <td>
                {a.connection_status}
                {a.tls_verify === false ? " (TLS verify off)" : ""}
              </td>
              <td className="max-w-xs truncate text-xs text-amber-800 dark:text-amber-300" title={a.last_poll_error ?? undefined}>
                {a.last_poll_error ?? "—"}
              </td>
              <td className="py-2 text-right">
                <AgentActions
                  agent={a}
                  testingId={testingId}
                  deletingId={deletingId}
                  onMetrics={() => setMetricsAgent(a)}
                  onMigrate={() => setMigrateAgent(a)}
                  onToggleTls={() => void handleToggleTls(a.id, a.tls_verify !== false)}
                  onTest={() => void handleTestConnection(a.id)}
                  onDelete={() => void handleDelete(a.id, a.name)}
                  inline
                />
              </td>
            </tr>
          ))}
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
      <AgentMigrateRegionDialog
        open={migrateAgent !== null}
        agent={migrateAgent}
        onClose={() => setMigrateAgent(null)}
        onMigrated={async () => {
          await invalidate();
          if (migrateAgent) {
            setOk(`Moved "${migrateAgent.name}" to the selected region.`);
          }
        }}
      />
    </div>
  );
}

function AgentActions({
  agent,
  testingId,
  deletingId,
  onMetrics,
  onMigrate,
  onToggleTls,
  onTest,
  onDelete,
  inline,
}: {
  agent: AgentOut;
  testingId: string | null;
  deletingId: string | null;
  onMetrics: () => void;
  onMigrate: () => void;
  onToggleTls: () => void;
  onTest: () => void;
  onDelete: () => void;
  inline?: boolean;
}) {
  const btn = inline
    ? "rounded border border-slate-300 dark:border-slate-600 px-2 py-1 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:bg-slate-800 disabled:opacity-50"
    : "text-sm text-slate-700 dark:text-slate-300";
  const delBtn = inline
    ? "rounded border border-red-300 dark:border-red-900/80 px-2 py-1 text-red-700 dark:text-red-300 hover:bg-red-50 dark:bg-red-950/40 disabled:opacity-50"
    : "text-sm text-red-700 dark:text-red-300";

  const buttons = (
    <>
      <button type="button" onClick={onMetrics} className={btn}>
        Metrics
      </button>
      <button type="button" onClick={onMigrate} className={btn}>
        Move region
      </button>
      <button type="button" onClick={onToggleTls} className={inline ? btn : "text-sm text-slate-600 dark:text-slate-400"}>
        {agent.tls_verify === false ? "Enable TLS verify" : "Disable TLS verify"}
      </button>
      <button
        type="button"
        onClick={onTest}
        disabled={testingId === agent.id}
        className={btn}
      >
        {testingId === agent.id ? "Testing…" : inline ? "Test" : "Test connection"}
      </button>
      <button
        type="button"
        onClick={onDelete}
        disabled={deletingId === agent.id}
        className={delBtn}
      >
        {deletingId === agent.id ? "Deleting…" : "Delete"}
      </button>
    </>
  );

  if (inline) {
    return <span className="inline-flex flex-wrap justify-end gap-1">{buttons}</span>;
  }
  return <div className="flex shrink-0 flex-col gap-1">{buttons}</div>;
}
