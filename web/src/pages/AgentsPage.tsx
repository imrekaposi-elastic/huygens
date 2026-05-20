import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthContext";
import { AgentRegisterDialog } from "@/components/AgentRegisterDialog";
import { api, ApiError } from "@/api/client";

export function AgentsPage() {
  const { selectedOrgId, organizations } = useAuth();
  const qc = useQueryClient();
  const [registerOpen, setRegisterOpen] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);

  const orgId = selectedOrgId ?? organizations[0]?.id;

  const { data, isLoading, error } = useQuery({
    queryKey: ["registry-agents"],
    queryFn: () => api.registryAgents(),
  });

  const agents = data?.filter((a) => !orgId || a.organization_id === orgId) ?? data;

  async function handleToggleTls(agentId: string, current: boolean) {
    setErr(null);
    try {
      await api.patchAgent(agentId, { tls_verify: !current });
      void qc.invalidateQueries({ queryKey: ["registry-agents"] });
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Update failed");
    }
  }

  async function handleTestConnection(agentId: string) {
    setErr(null);
    setTestingId(agentId);
    try {
      await api.testAgentConnection(agentId);
      void qc.invalidateQueries({ queryKey: ["registry-agents"] });
      void qc.invalidateQueries({ queryKey: ["dashboard"] });
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
      void qc.invalidateQueries({ queryKey: ["registry-agents"] });
      void qc.invalidateQueries({ queryKey: ["dashboard"] });
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  if (isLoading) return <p className="text-slate-400">Loading…</p>;
  if (error) return <p className="text-red-400">{(error as Error).message}</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Agents</h1>
          <p className="text-sm text-slate-500">Platform admin — registry enrollment</p>
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
        <p className="text-sm text-amber-300">Select an organization in the header to register an agent.</p>
      )}
      {err && <p className="text-sm text-red-400">{err}</p>}
      <div className="space-y-2 md:hidden">
        {agents?.map((a) => (
          <div
            key={a.id}
            className="flex items-start justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900 p-3"
          >
            <div className="min-w-0">
              <p className="font-medium">{a.name}</p>
              <p className="truncate text-xs text-slate-500">{a.base_url}</p>
              <p className="text-sm">
                {a.connection_status}
                {a.tls_verify === false ? " · TLS verify off" : ""}
              </p>
              {a.last_poll_error && (
                <p className="text-xs text-amber-300">{a.last_poll_error}</p>
              )}
            </div>
            <div className="flex shrink-0 flex-col gap-1">
              <button
                type="button"
                onClick={() => void handleToggleTls(a.id, a.tls_verify !== false)}
                className="text-sm text-slate-400"
              >
                {a.tls_verify === false ? "Enable TLS verify" : "Disable TLS verify"}
              </button>
              <button
                type="button"
                onClick={() => void handleTestConnection(a.id)}
                disabled={testingId === a.id}
                className="text-sm text-slate-300"
              >
                {testingId === a.id ? "Testing…" : "Test"}
              </button>
              <button
                type="button"
                onClick={() => void handleDelete(a.id, a.name)}
                disabled={deletingId === a.id}
                className="text-sm text-red-300"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
      <table className="hidden w-full text-sm md:table">
        <thead className="text-slate-500">
          <tr>
            <th className="pb-2 text-left">Name</th>
            <th>Base URL</th>
            <th>Status</th>
            <th>Error</th>
            <th className="pb-2 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {agents?.map((a) => (
            <tr key={a.id} className="border-t border-slate-800">
              <td className="py-2">{a.name}</td>
              <td className="font-mono text-xs">{a.base_url}</td>
              <td>
                {a.connection_status}
                {a.tls_verify === false ? " (TLS verify off)" : ""}
              </td>
              <td className="max-w-xs truncate text-xs text-amber-300" title={a.last_poll_error ?? undefined}>
                {a.last_poll_error ?? "—"}
              </td>
              <td className="py-2 text-right space-x-2">
                <button
                  type="button"
                  onClick={() => void handleToggleTls(a.id, a.tls_verify !== false)}
                  className="rounded border border-slate-600 px-2 py-1 text-slate-400 hover:bg-slate-800"
                >
                  {a.tls_verify === false ? "Enable TLS verify" : "Disable TLS verify"}
                </button>
                <button
                  type="button"
                  onClick={() => void handleTestConnection(a.id)}
                  disabled={testingId === a.id}
                  className="rounded border border-slate-600 px-2 py-1 text-slate-300 hover:bg-slate-800 disabled:opacity-50"
                >
                  {testingId === a.id ? "Testing…" : "Test connection"}
                </button>
                <button
                  type="button"
                  onClick={() => void handleDelete(a.id, a.name)}
                  disabled={deletingId === a.id}
                  className="rounded border border-red-900/80 px-2 py-1 text-red-300 hover:bg-red-950/40 disabled:opacity-50"
                >
                  {deletingId === a.id ? "Deleting…" : "Delete"}
                </button>
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
          onRegistered={() => {
            void qc.invalidateQueries({ queryKey: ["registry-agents"] });
          }}
        />
      )}
    </div>
  );
}
