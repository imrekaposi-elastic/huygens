import type { ReactNode } from "react";
import {
  formatVmDisks,
  guestReachabilityNote,
  hypervisorPowerLabel,
  type VmDiskInfo,
} from "@/lib/vmStatus";

export type VmRow = {
  name?: string;
  server_name?: string;
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
    return <p className="text-slate-400">Loading…</p>;
  }
  if (vms.length === 0) {
    return (
      <p className="rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-8 text-center text-sm text-slate-500">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-900/50">
      <table className="w-full min-w-[640px] text-left text-sm">
        <thead>
          <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
            <th className="px-4 py-2 font-medium">Server</th>
            <th className="px-4 py-2 font-medium">vCPU</th>
            <th className="px-4 py-2 font-medium">Memory (MB)</th>
            <th className="px-4 py-2 font-medium">Disks</th>
            <th className="px-4 py-2 font-medium">Power</th>
            <th className="px-4 py-2 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {vms.map((vm) => {
            const name = String(vm.name ?? "");
            const server = String(vm.server_name ?? name);
            const power = hypervisorPowerLabel(vm.libvirt_state);
            const note = guestReachabilityNote(vm.status, vm.libvirt_state);
            return (
              <tr key={name}>
                <td className="px-4 py-3">
                  <p className="font-medium text-slate-100">{server}</p>
                  {server !== name && (
                    <p className="text-xs text-slate-500 font-mono">{name}</p>
                  )}
                  {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
                </td>
                <td className="px-4 py-3 text-slate-300">{vm.vcpu ?? "—"}</td>
                <td className="px-4 py-3 text-slate-300">{vm.memory_mib ?? "—"}</td>
                <td className="max-w-xs px-4 py-3 text-xs text-slate-400">
                  {formatVmDisks(vm.disks)}
                </td>
                <td className="px-4 py-3">
                  <span className={`inline-block rounded px-2 py-0.5 text-xs ${power.className}`}>
                    {power.label}
                  </span>
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
