import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export function AgentsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["registry-agents"],
    queryFn: () => api.registryAgents(),
  });

  if (isLoading) return <p className="text-slate-400">Loading…</p>;
  if (error) return <p className="text-red-400">{(error as Error).message}</p>;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Agents (registry)</h1>
      <p className="text-sm text-slate-500">Platform admin view — registration via API</p>
      <div className="space-y-2 md:hidden">
        {data?.map((a) => (
          <div key={a.id} className="rounded-lg border border-slate-800 bg-slate-900 p-3">
            <p className="font-medium">{a.name}</p>
            <p className="text-xs text-slate-500">{a.base_url}</p>
            <p className="text-sm">{a.connection_status}</p>
          </div>
        ))}
      </div>
      <table className="hidden w-full text-sm md:table">
        <thead className="text-slate-500">
          <tr>
            <th className="pb-2 text-left">Name</th>
            <th>Base URL</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {data?.map((a) => (
            <tr key={a.id} className="border-t border-slate-800">
              <td className="py-2">{a.name}</td>
              <td className="font-mono text-xs">{a.base_url}</td>
              <td>{a.connection_status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
