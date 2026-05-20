import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthContext";
import { api } from "@/api/client";
import { useInventoryEvents } from "@/hooks/useInventoryEvents";

export function DashboardPage() {
  const { selectedOrgId } = useAuth();
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard", selectedOrgId],
    queryFn: () => api.dashboard(selectedOrgId!),
    enabled: !!selectedOrgId,
  });

  useInventoryEvents(selectedOrgId, !!selectedOrgId);

  if (!selectedOrgId) return <p className="text-slate-400">Select an organization</p>;
  if (isLoading) return <p className="text-slate-400">Loading…</p>;
  if (error) return <p className="text-red-400">{(error as Error).message}</p>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Inventory dashboard</h1>
      <p className="text-sm text-slate-500">Live updates via SSE (fetch + Bearer)</p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          ["Agents", data.agent_count],
          ["VMs", data.vm_count],
          ["Networks", data.network_count],
          ["Drift", data.agents_with_drift],
        ].map(([label, value]) => (
          <div key={label as string} className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <p className="text-xs text-slate-500">{label}</p>
            <p className="text-2xl font-semibold">{value}</p>
          </div>
        ))}
      </div>
      <section>
        <h2 className="mb-3 text-lg font-medium">Agents</h2>
        <div className="space-y-2 md:hidden">
          {data.agents.map((a) => (
            <AgentCard key={a.agent_id} agent={a} />
          ))}
        </div>
        <table className="hidden w-full text-left text-sm md:table">
          <thead className="text-slate-500">
            <tr>
              <th className="pb-2">Agent</th>
              <th>VMs</th>
              <th>Networks</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.agents.map((a) => (
              <tr key={a.agent_id} className="border-t border-slate-800">
                <td className="py-2 font-mono text-xs">{a.agent_id.slice(0, 8)}…</td>
                <td>{a.vm_count}</td>
                <td>{a.network_count}</td>
                <td>
                  {a.poll_error ? (
                    <span className="text-red-400">error</span>
                  ) : (
                    (a.connection_status ?? "—")
                  )}
                  {a.config_drift && (
                    <span className="ml-2 rounded bg-amber-950 px-1 text-amber-300">drift</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function AgentCard({ agent }: { agent: import("@/api/types").AgentInventorySummary }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
      <p className="font-mono text-xs text-slate-400">{agent.agent_id.slice(0, 8)}…</p>
      <p className="mt-1 text-sm">
        {agent.vm_count} VMs · {agent.network_count} networks
      </p>
      {agent.config_drift && (
        <span className="mt-2 inline-block rounded bg-amber-950 px-2 py-0.5 text-xs text-amber-300">
          drift
        </span>
      )}
    </div>
  );
}
