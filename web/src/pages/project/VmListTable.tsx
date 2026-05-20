import type { ReactNode } from "react";
import {
  formatVmDisks,
  hypervisorPowerLabel,
  isSshReachable,
  type VmDiskInfo,
} from "@/lib/vmStatus";

export type VmRow = {
  name?: string;
  server_name?: string;
  network?: string;
  guest_ip?: string | null;
  vcpu?: number;
  memory_mib?: number;
  disks?: VmDiskInfo[];
  libvirt_state?: string;
  status?: string;
};

type Props = {
  vms: VmRow[];
  loading?: boolean;
  emptyMessage: string;
  actions: (vm: VmRow) => ReactNode;
};

export function VmListTable({ vms, loading, emptyMessage, actions }: Props) {
  if (loading) {
    return <p className="text-slate-600 dark:text-slate-400">Loading…</p>;
  }
  if (vms.length === 0) {
    return (
      <p className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100/90 dark:bg-slate-900/50 px-4 py-8 text-center text-sm text-slate-500 dark:text-slate-500">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-100/90 dark:bg-slate-900/50">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead>
          <tr className="border-b border-slate-200 dark:border-slate-800 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-500">
            <th className="px-4 py-2 font-medium">Server</th>
            <th className="px-4 py-2 font-medium">Network</th>
            <th className="px-4 py-2 font-medium">vCPU</th>
            <th className="px-4 py-2 font-medium">Memory (MB)</th>
            <th className="px-4 py-2 font-medium">Disks</th>
            <th className="px-4 py-2 font-medium">Power</th>
            <th className="px-4 py-2 font-medium text-center">SSH</th>
            <th className="px-4 py-2 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
          {vms.map((vm) => {
            const name = String(vm.name ?? "");
            const server = String(vm.server_name ?? name);
            const power = hypervisorPowerLabel(vm.libvirt_state);
            const sshOk = isSshReachable(vm.status);
            const sshTitle =
              vm.status === "degraded"
                ? "Guest running but SSH probe failed or slow"
                : sshOk
                  ? "Reachable on port 22"
                  : vm.libvirt_state?.toUpperCase() !== "RUNNING"
                    ? "VM not running on hypervisor"
                    : "Not reachable on port 22 (no guest IP or firewall)";
            return (
              <tr key={name}>
                <td className="px-4 py-3">
                  <p className="font-medium text-slate-900 dark:text-slate-100">{server}</p>
                  {server !== name && (
                    <p className="text-xs text-slate-500 dark:text-slate-500 font-mono">{name}</p>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-700 dark:text-slate-300">
                  <p>{vm.network ?? "—"}</p>
                  {vm.guest_ip && (
                    <p className="text-xs text-slate-500 dark:text-slate-500 font-mono">{vm.guest_ip}</p>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{vm.vcpu ?? "—"}</td>
                <td className="px-4 py-3 text-slate-700 dark:text-slate-300">{vm.memory_mib ?? "—"}</td>
                <td className="max-w-xs px-4 py-3 text-xs text-slate-600 dark:text-slate-400">
                  {formatVmDisks(vm.disks)}
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-block rounded px-2 py-0.5 text-xs ${power.className}`}>
                    {power.label}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <input
                    type="checkbox"
                    readOnly
                    checked={sshOk}
                    title={sshTitle}
                    aria-label={sshTitle}
                    className="size-4 cursor-default accent-emerald-500"
                  />
                </td>
                <td className="px-4 py-3 text-right">{actions(vm)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
