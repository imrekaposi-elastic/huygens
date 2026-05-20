import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthContext";
import { api } from "@/api/client";
import { AssignToProjectControl } from "@/components/AssignToProjectControl";
import { useInventoryEvents } from "@/hooks/useInventoryEvents";
import type { AgentInventorySummary, NetworkInventoryItem, VmInventoryItem } from "@/api/types";
import { filterManagedNetworks } from "@/lib/systemNetwork";
import { formatVmStatusLine, guestStatusHint } from "@/lib/vmStatus";

export function DashboardPage() {
  const { selectedOrgId } = useAuth();
  const orgId = selectedOrgId!;
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

  const totalOrphanedVms = data.agents.reduce((n, a) => n + a.orphaned_vm_count, 0);
  const totalOrphanedNets = data.agents.reduce((n, a) => n + a.orphaned_network_count, 0);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Inventory dashboard</h1>
      <p className="text-sm text-slate-500">
        Discovered on agents. VMs and networks are <strong className="text-amber-200">unassigned</strong> until
        added to a project (via Projects → agent proxy).
      </p>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          ["Agents", data.agent_count],
          ["VMs", data.vm_count],
          ["Networks", data.network_count],
          ["Changed", data.agents_with_drift],
        ].map(([label, value]) => (
          <div key={label as string} className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <p className="text-xs text-slate-500">{label}</p>
            <p className="text-2xl font-semibold">{value}</p>
          </div>
        ))}
      </div>
      {(totalOrphanedVms > 0 || totalOrphanedNets > 0) && (
        <p className="rounded-lg border border-amber-900/60 bg-amber-950/30 px-4 py-3 text-sm text-amber-100">
          {totalOrphanedVms > 0 && (
            <span>
              {totalOrphanedVms} VM{totalOrphanedVms === 1 ? "" : "s"} not in any project
            </span>
          )}
          {totalOrphanedVms > 0 && totalOrphanedNets > 0 && " · "}
          {totalOrphanedNets > 0 && (
            <span>
              {totalOrphanedNets} network{totalOrphanedNets === 1 ? "" : "s"} not in any project
            </span>
          )}
          <span className="text-amber-200/80"> — assign them under </span>
          <Link to="/projects" className="font-medium text-amber-200 underline">
            Projects
          </Link>
        </p>
      )}
      <section className="space-y-4">
        <h2 className="text-lg font-medium">Agents</h2>
        {data.agents.length === 0 ? (
          <p className="text-sm text-slate-500">No enrolled agents with inventory yet.</p>
        ) : (
          data.agents.map((a) => (
            <AgentInventoryPanel key={a.agent_id} agent={a} organizationId={orgId} />
          ))
        )}
      </section>
    </div>
  );
}

function AgentInventoryPanel({
  agent,
  organizationId,
}: {
  agent: AgentInventorySummary;
  organizationId: string;
}) {
  const title = agent.agent_name ?? agent.agent_id;

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900">
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-slate-800 px-4 py-3">
        <div>
          <h3 className="font-medium text-white">{title}</h3>
          {agent.agent_name && (
            <p className="font-mono text-xs text-slate-500">{agent.agent_id}</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {agent.poll_error ? (
            <span className="text-red-400">poll error</span>
          ) : (
            <span className="text-slate-400">{agent.connection_status ?? "—"}</span>
          )}
          {agent.config_drift && (
            <span
              className="rounded bg-amber-950 px-2 py-0.5 text-xs text-amber-300"
              title="VM or network inventory changed since the previous successful poll"
            >
              changed
            </span>
          )}
          <span className="text-slate-500">
            {agent.vm_count} VMs · {agent.network_count} networks
            {(agent.orphaned_vm_count > 0 || agent.orphaned_network_count > 0) && (
              <span className="text-amber-300/90">
                {" "}
                ({agent.orphaned_vm_count} unassigned VM
                {agent.orphaned_vm_count === 1 ? "" : "s"}
                {agent.orphaned_network_count > 0 &&
                  `, ${agent.orphaned_network_count} unassigned network${agent.orphaned_network_count === 1 ? "" : "s"}`}
                )
              </span>
            )}
          </span>
        </div>
      </div>

      <div className="grid gap-4 p-4 md:grid-cols-2">
        <ResourceInventoryList
          title="Virtual machines"
          empty="No VMs reported by this agent."
          items={agent.vms}
          renderItem={(vm) => (
            <VmRow vm={vm} organizationId={organizationId} agentId={agent.agent_id} />
          )}
        />
        <div>
          <ResourceInventoryList
            title="Virtual networks"
            empty="No operator-managed networks on this agent."
            items={filterManagedNetworks(agent.networks)}
            renderItem={(net) => (
              <NetworkRow net={net} organizationId={organizationId} agentId={agent.agent_id} />
            )}
          />
          <p className="mt-2 text-xs text-slate-600">
            The libvirt <span className="font-mono">default</span> network is system-managed and not
            listed or assignable.
          </p>
        </div>
      </div>
    </div>
  );
}

function ResourceInventoryList<T extends { name: string | null; orphaned: boolean }>({
  title,
  empty,
  items,
  renderItem,
}: {
  title: string;
  empty: string;
  items: T[];
  renderItem: (item: T) => React.ReactNode;
}) {
  const orphaned = items.filter((i) => i.orphaned);
  const assigned = items.filter((i) => !i.orphaned);

  if (items.length === 0) {
    return (
      <div>
        <h4 className="mb-2 text-sm font-medium text-slate-300">{title}</h4>
        <p className="text-sm text-slate-500">{empty}</p>
      </div>
    );
  }

  return (
    <div>
      <h4 className="mb-2 text-sm font-medium text-slate-300">{title}</h4>
      {orphaned.length > 0 && (
        <div className="mb-3">
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-amber-400/90">
            Unassigned — not in a project
          </p>
          <ul className="space-y-1.5">
            {orphaned.map((item) => (
              <div key={item.name ?? `orphan-${title}`}>{renderItem(item)}</div>
            ))}
          </ul>
        </div>
      )}
      {assigned.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-emerald-400/90">
            In a project
          </p>
          <ul className="space-y-1.5">
            {assigned.map((item) => (
              <div key={item.name ?? `assigned-${title}`}>{renderItem(item)}</div>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function AssignmentBadge({
  orphaned,
  projectName,
  projectId,
}: {
  orphaned: boolean;
  projectName: string | null;
  projectId: string | null;
}) {
  if (orphaned) {
    return (
      <span className="shrink-0 rounded border border-dashed border-amber-700/80 bg-amber-950/50 px-2 py-0.5 text-xs font-medium text-amber-200">
        Unassigned
      </span>
    );
  }
  if (projectId && projectName) {
    return (
      <Link
        to="/projects/$projectId"
        params={{ projectId }}
        className="shrink-0 rounded border border-emerald-800/80 bg-emerald-950/40 px-2 py-0.5 text-xs font-medium text-emerald-200 hover:bg-emerald-950/70"
      >
        {projectName}
      </Link>
    );
  }
  return null;
}

function VmRow({
  vm,
  organizationId,
  agentId,
}: {
  vm: VmInventoryItem;
  organizationId: string;
  agentId: string;
}) {
  const secondary = [
    formatVmStatusLine(vm),
    vm.networks.length ? `on ${vm.networks.join(", ")}` : null,
    vm.ips.length ? vm.ips.join(", ") : null,
  ]
    .filter(Boolean)
    .join(" · ");
  const hint = guestStatusHint(vm.guest_status);

  return (
    <li
      className={
        vm.orphaned
          ? "rounded border border-dashed border-amber-800/50 bg-amber-950/20 px-3 py-2"
          : "rounded border border-emerald-900/40 bg-emerald-950/15 px-3 py-2"
      }
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="font-medium text-slate-200">{vm.name ?? "—"}</span>
          {secondary ? <span className="mt-0.5 block text-xs text-slate-500">{secondary}</span> : null}
          {hint ? <span className="mt-0.5 block text-xs text-amber-400/90">{hint}</span> : null}
        </div>
        {vm.orphaned && vm.name ? (
          <AssignToProjectControl
            organizationId={organizationId}
            agentId={agentId}
            resourceType="vm"
            resourceName={vm.name}
          />
        ) : (
          <AssignmentBadge
            orphaned={vm.orphaned}
            projectName={vm.project_name}
            projectId={vm.project_id}
          />
        )}
      </div>
    </li>
  );
}

function NetworkRow({
  net,
  organizationId,
  agentId,
}: {
  net: NetworkInventoryItem;
  organizationId: string;
  agentId: string;
}) {
  const secondary = [
    net.active === false ? "inactive" : net.active ? "active" : null,
    net.readonly ? "readonly" : null,
    net.bridge ? `bridge ${net.bridge}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <li
      className={
        net.orphaned
          ? "rounded border border-dashed border-amber-800/50 bg-amber-950/20 px-3 py-2"
          : "rounded border border-emerald-900/40 bg-emerald-950/15 px-3 py-2"
      }
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="font-medium text-slate-200">{net.name ?? "—"}</span>
          {secondary ? <span className="mt-0.5 block text-xs text-slate-500">{secondary}</span> : null}
        </div>
        {net.orphaned && net.name ? (
          <AssignToProjectControl
            organizationId={organizationId}
            agentId={agentId}
            resourceType="network"
            resourceName={net.name}
          />
        ) : (
          <AssignmentBadge
            orphaned={net.orphaned}
            projectName={net.project_name}
            projectId={net.project_id}
          />
        )}
      </div>
    </li>
  );
}
