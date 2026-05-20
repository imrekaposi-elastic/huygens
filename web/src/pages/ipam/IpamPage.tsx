import { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { IpAllocation, Project, WizardSubnetPlan } from "@/api/types";
import { NetworkIcon, PageTitleIcon } from "@/components/icons/NavIcons";
import { addressesInSubnet, hostsToPrefixLen, subnetMaskLabel } from "@/lib/ipam";

type Props = {
  organizationId: string;
};

export function IpamPage({ organizationId }: Props) {
  const qc = useQueryClient();
  const [poolId, setPoolId] = useState("");
  const [newPoolName, setNewPoolName] = useState("org-private");
  const [newPoolCidr, setNewPoolCidr] = useState("10.100.0.0/16");
  const [assignProjectId, setAssignProjectId] = useState("");
  const [networkCount, setNetworkCount] = useState("3");
  const [hostsPerNetwork, setHostsPerNetwork] = useState("50");
  const [plan, setPlan] = useState<WizardSubnetPlan[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const pools = useQuery({
    queryKey: ["ipam-pools", organizationId],
    queryFn: () => api.listIpamPools(organizationId),
    enabled: !!organizationId,
  });

  const projects = useQuery({
    queryKey: ["projects", organizationId],
    queryFn: () => api.projects(organizationId),
    enabled: !!organizationId,
  });

  const activePoolId = poolId || pools.data?.[0]?.id || "";
  const hosts = Math.max(1, parseInt(hostsPerNetwork, 10) || 50);
  const prefixLen = hostsToPrefixLen(hosts);

  const poolAllocations = useQuery({
    queryKey: ["ipam-pool-allocations", organizationId, activePoolId],
    queryFn: () => api.listPoolAllocations(organizationId, activePoolId),
    enabled: !!organizationId && !!activePoolId,
  });

  const projectById = useMemo(() => {
    const map = new Map<string, Project>();
    for (const p of projects.data ?? []) {
      map.set(p.id, p);
    }
    return map;
  }, [projects.data]);

  const createPool = useMutation({
    mutationFn: () =>
      api.createIpamPool(organizationId, {
        name: newPoolName.trim(),
        cidr: newPoolCidr.trim(),
        description: "Organization private address space",
      }),
    onSuccess: (pool) => {
      setPoolId(pool.id);
      setPlan(null);
      setOk(`Created address pool ${pool.name} (${pool.cidr}).`);
      void qc.invalidateQueries({ queryKey: ["ipam-pools", organizationId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Create pool failed"),
  });

  const runPlan = useMutation({
    mutationFn: () =>
      api.ipamWizardPlan(organizationId, {
        pool_id: activePoolId,
        network_count: Math.max(1, parseInt(networkCount, 10) || 1),
        hosts_per_network: hosts,
      }),
    onSuccess: (res) => {
      setPlan(res.subnets);
      setErr(null);
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Planning failed"),
  });

  const applyPlan = useMutation({
    mutationFn: () => {
      if (!plan?.length) throw new Error("Calculate subnets first");
      if (!assignProjectId) throw new Error("Select a project");
      return api.ipamWizardApply(organizationId, assignProjectId, {
        pool_id: activePoolId,
        subnets: plan.map((s) => ({ cidr: s.cidr, name: s.suggested_name })),
      });
    },
    onSuccess: (rows) => {
      setPlan(null);
      setOk(
        `Assigned ${rows.length} subnet block${rows.length === 1 ? "" : "s"} to ${projectById.get(assignProjectId)?.name ?? "project"}.`,
      );
      void qc.invalidateQueries({ queryKey: ["ipam-pool-allocations", organizationId, activePoolId] });
      void qc.invalidateQueries({ queryKey: ["ipam-allocations", organizationId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Assign failed"),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold">
          <PageTitleIcon>
            <NetworkIcon />
          </PageTitleIcon>
          IPAM
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-500">
          Organization-wide private address space. Assign subnet blocks to projects here; project teams
          then create libvirt networks from those blocks without manual CIDR planning.
        </p>
      </div>

      {ok && <p className="text-sm text-emerald-600 dark:text-emerald-400">{ok}</p>}
      {err && <p className="text-sm text-red-700 dark:text-red-300">{err}</p>}

      <section className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/80 p-4">
        <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">Organization address pool</h2>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
          One RFC1918 pool per organization keeps address spaces unique for cross-project linking (phase 6).
        </p>

        {(pools.data?.length ?? 0) === 0 ? (
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <label className="block text-sm md:col-span-1">
              Pool name
              <input
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
                value={newPoolName}
                onChange={(e) => setNewPoolName(e.target.value)}
              />
            </label>
            <label className="block text-sm md:col-span-2">
              Organization CIDR (RFC1918)
              <input
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
                value={newPoolCidr}
                onChange={(e) => setNewPoolCidr(e.target.value)}
                placeholder="10.100.0.0/16"
              />
            </label>
            <div className="md:col-span-3">
              <button
                type="button"
                disabled={createPool.isPending}
                onClick={() => {
                  setErr(null);
                  setOk(null);
                  createPool.mutate();
                }}
                className="min-h-10 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
              >
                {createPool.isPending ? "Creating…" : "Create organization pool"}
              </button>
            </div>
          </div>
        ) : (
          <label className="mt-4 block text-sm">
            Active pool
            <select
              className="mt-1 w-full max-w-xl min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
              value={activePoolId}
              onChange={(e) => {
                setPoolId(e.target.value);
                setPlan(null);
              }}
            >
              {pools.data?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} — {p.cidr}
                </option>
              ))}
            </select>
          </label>
        )}
      </section>

      {activePoolId && (
        <>
          <section className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/80 p-4">
            <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">Assignments</h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
              Subnet blocks carved from the pool and bound to projects.
            </p>
            {poolAllocations.isLoading ? (
              <p className="mt-3 text-sm text-slate-500 dark:text-slate-500">Loading…</p>
            ) : (poolAllocations.data?.length ?? 0) === 0 ? (
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">No assignments in this pool yet.</p>
            ) : (
              <table className="mt-3 w-full text-sm">
                <thead className="text-left text-xs text-slate-500 dark:text-slate-500">
                  <tr>
                    <th className="pb-2 pr-4">CIDR</th>
                    <th className="pb-2 pr-4">Project</th>
                    <th className="pb-2 pr-4">Status</th>
                    <th className="pb-2">Network</th>
                  </tr>
                </thead>
                <tbody>
                  {poolAllocations.data?.map((row) => (
                    <AllocationTableRow key={row.id} row={row} project={projectById.get(row.project_id)} />
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/80 p-4">
            <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">Subnet wizard</h2>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
              Estimate how many VMs you need per virtual network; the mask is calculated automatically.
            </p>

            {(projects.data?.length ?? 0) === 0 ? (
              <p className="mt-3 text-sm text-amber-800 dark:text-amber-300">
                <Link to="/projects" className="underline">
                  Create a project
                </Link>{" "}
                before assigning subnets.
              </p>
            ) : (
              <div className="mt-4 space-y-4">
                <label className="block text-sm max-w-md">
                  Assign to project
                  <select
                    className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                    value={assignProjectId}
                    onChange={(e) => setAssignProjectId(e.target.value)}
                  >
                    <option value="">Select project…</option>
                    {projects.data?.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.slug})
                      </option>
                    ))}
                  </select>
                </label>
                <div className="grid gap-3 sm:grid-cols-2 max-w-2xl">
                  <label className="block text-sm">
                    Virtual networks needed
                    <input
                      type="number"
                      min={1}
                      max={64}
                      className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                      value={networkCount}
                      onChange={(e) => {
                        setNetworkCount(e.target.value);
                        setPlan(null);
                      }}
                    />
                  </label>
                  <label className="block text-sm">
                    Expected hosts per network
                    <input
                      type="number"
                      min={1}
                      max={4096}
                      className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                      value={hostsPerNetwork}
                      onChange={(e) => {
                        setHostsPerNetwork(e.target.value);
                        setPlan(null);
                      }}
                    />
                    <span className="mt-1 block text-xs text-emerald-700 dark:text-emerald-400">
                      Mask {subnetMaskLabel(hosts)} — ~{addressesInSubnet(prefixLen)} usable addresses each
                    </span>
                  </label>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={runPlan.isPending || !activePoolId}
                    onClick={() => {
                      setErr(null);
                      setOk(null);
                      runPlan.mutate();
                    }}
                    className="min-h-10 rounded-lg border border-slate-300 dark:border-slate-600 px-4 text-sm hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
                  >
                    {runPlan.isPending ? "Calculating…" : "1. Calculate subnets"}
                  </button>
                  <button
                    type="button"
                    disabled={applyPlan.isPending || !plan?.length || !assignProjectId}
                    onClick={() => {
                      setErr(null);
                      setOk(null);
                      applyPlan.mutate();
                    }}
                    className="min-h-10 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
                  >
                    {applyPlan.isPending ? "Assigning…" : "2. Assign to project"}
                  </button>
                </div>
                {plan && plan.length > 0 && (
                  <table className="w-full max-w-2xl text-sm">
                    <thead className="text-left text-xs text-slate-500 dark:text-slate-500">
                      <tr>
                        <th className="pb-1 pr-4">Suggested name</th>
                        <th className="pb-1">CIDR</th>
                        <th className="pb-1">Mask</th>
                      </tr>
                    </thead>
                    <tbody>
                      {plan.map((row) => {
                        const plen = parseInt(row.cidr.split("/")[1] ?? "24", 10);
                        return (
                          <tr
                            key={row.cidr}
                            className="border-t border-slate-200 dark:border-slate-800 font-mono text-xs"
                          >
                            <td className="py-1.5 pr-4 text-slate-700 dark:text-slate-300">
                              {row.suggested_name}
                            </td>
                            <td className="py-1.5">{row.cidr}</td>
                            <td className="py-1.5 text-slate-500">/{plen}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function AllocationTableRow({
  row,
  project,
}: {
  row: IpAllocation;
  project: Project | undefined;
}) {
  const status =
    row.status === "allocated"
      ? row.network_name
        ? `in use · ${row.network_name}`
        : "in use"
      : "reserved";
  return (
    <tr className="border-t border-slate-200 dark:border-slate-800">
      <td className="py-2 pr-4 font-mono text-slate-800 dark:text-slate-200">{row.cidr}</td>
      <td className="py-2 pr-4">
        {project ? (
          <Link
            to="/projects/$projectId/networks"
            params={{ projectId: project.id }}
            className="text-emerald-600 dark:text-emerald-400 hover:underline"
          >
            {project.name}
          </Link>
        ) : (
          <span className="text-slate-500">{row.project_id.slice(0, 8)}…</span>
        )}
      </td>
      <td className="py-2 pr-4 text-xs text-slate-600 dark:text-slate-400">{status}</td>
      <td className="py-2 text-xs text-slate-500">{row.network_name ?? "—"}</td>
    </tr>
  );
}
