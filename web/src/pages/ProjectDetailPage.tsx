import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";

type Props = { projectId: string };

export function ProjectDetailPage({ projectId }: Props) {
  const qc = useQueryClient();
  const [agentId, setAgentId] = useState<string>("");
  const [vmName, setVmName] = useState("");
  const [netName, setNetName] = useState("");
  const [netHosts, setNetHosts] = useState("10");
  const [msg, setMsg] = useState<string | null>(null);

  const agents = useQuery({
    queryKey: ["project-agents", projectId],
    queryFn: () => api.projectAgents(projectId),
  });

  const vms = useQuery({
    queryKey: ["vms", projectId, agentId],
    queryFn: () => api.listVms(projectId, agentId),
    enabled: !!agentId,
  });

  const networks = useQuery({
    queryKey: ["networks", projectId, agentId],
    queryFn: () => api.listNetworks(projectId, agentId),
    enabled: !!agentId,
  });

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ["vms", projectId, agentId] });
    void qc.invalidateQueries({ queryKey: ["networks", projectId, agentId] });
  };

  const createVm = useMutation({
    mutationFn: () =>
      api.createVm(projectId, agentId, {
        name: vmName,
        vcpus: 1,
        memory_mb: 1024,
        disk_gb: 10,
      }),
    onSuccess: () => {
      setVmName("");
      setMsg(null);
      invalidate();
    },
    onError: (e) => setMsg(e instanceof ApiError ? e.message : "Failed"),
  });

  const createNet = useMutation({
    mutationFn: () =>
      api.createNetwork(projectId, agentId, {
        name: netName,
        ipam: { hosts: parseInt(netHosts, 10) || 10 },
      }),
    onSuccess: () => {
      setNetName("");
      setMsg(null);
      invalidate();
    },
    onError: (e) => setMsg(e instanceof ApiError ? e.message : "Failed"),
  });

  const deleteVm = useMutation({
    mutationFn: (name: string) => api.deleteVm(projectId, agentId, name),
    onSuccess: invalidate,
  });

  const deleteNet = useMutation({
    mutationFn: (name: string) => api.deleteNetwork(projectId, agentId, name),
    onSuccess: invalidate,
    onError: (e) => setMsg(e instanceof ApiError ? e.message : "Delete failed"),
  });

  return (
    <div className="space-y-6">
      <Link to="/projects" className="text-sm text-emerald-400 hover:underline">
        ← Projects
      </Link>
      <h1 className="text-2xl font-semibold">Project workloads</h1>
      {msg && <p className="text-sm text-amber-300">{msg}</p>}

      <label className="block text-sm">
        Agent
        <select
          className="mt-1 min-h-11 w-full max-w-md rounded border border-slate-700 bg-slate-800 px-3"
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

      {!agentId ? (
        <p className="text-slate-500">Pick an agent to manage VMs and networks</p>
      ) : (
        <>
          <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <h2 className="font-medium">Virtual machines</h2>
            <form
              className="mt-3 flex flex-wrap gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                createVm.mutate();
              }}
            >
              <input
                className="min-h-11 flex-1 rounded border border-slate-700 bg-slate-800 px-3"
                placeholder="vm name"
                value={vmName}
                onChange={(e) => setVmName(e.target.value)}
                required
              />
              <button type="submit" className="min-h-11 rounded bg-emerald-600 px-4">
                Create VM
              </button>
            </form>
            <ul className="mt-3 space-y-2">
              {vms.data?.map((vm) => {
                const name = String(vm.name ?? "");
                return (
                  <li
                    key={name}
                    className="flex items-center justify-between rounded border border-slate-800 px-3 py-2"
                  >
                    <span>{name}</span>
                    <button
                      type="button"
                      className="text-sm text-red-400"
                      onClick={() => deleteVm.mutate(name)}
                    >
                      Delete
                    </button>
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <h2 className="font-medium">Networks</h2>
            <form
              className="mt-3 flex flex-wrap gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                createNet.mutate();
              }}
            >
              <input
                className="min-h-11 rounded border border-slate-700 bg-slate-800 px-3"
                placeholder="network name"
                value={netName}
                onChange={(e) => setNetName(e.target.value)}
                required
              />
              <input
                className="min-h-11 w-24 rounded border border-slate-700 bg-slate-800 px-3"
                placeholder="hosts"
                value={netHosts}
                onChange={(e) => setNetHosts(e.target.value)}
                title="IPAM hosts count"
              />
              <button type="submit" className="min-h-11 rounded bg-emerald-600 px-4">
                Create network
              </button>
            </form>
            <ul className="mt-3 space-y-2">
              {networks.data?.map((net) => {
                const name = String(net.name ?? "");
                const readonly = Boolean(net.readonly);
                return (
                  <li
                    key={name}
                    className="flex items-center justify-between rounded border border-slate-800 px-3 py-2"
                  >
                    <span>
                      {name}
                      {readonly && (
                        <span className="ml-2 rounded bg-slate-800 px-2 text-xs text-slate-400">
                          readonly
                        </span>
                      )}
                    </span>
                    {!readonly && (
                      <button
                        type="button"
                        className="text-sm text-red-400"
                        onClick={() => deleteNet.mutate(name)}
                      >
                        Delete
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
