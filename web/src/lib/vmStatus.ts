/** VM status from libvirt agent: hypervisor state vs SSH guest probe. */

export type VmDiskInfo = {
  device?: string;
  path?: string | null;
  size_bytes?: number | null;
};

export function formatBytes(bytes: number): string {
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
  if (bytes >= 1024 ** 2) return `${(bytes / 1024 ** 2).toFixed(0)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${bytes} B`;
}

export function formatVmDisks(disks: VmDiskInfo[] | undefined): string {
  if (!disks?.length) return "—";
  return disks
    .map((d) => {
      const file = d.path ? d.path.split("/").pop() : null;
      const size = d.size_bytes != null ? formatBytes(d.size_bytes) : "";
      const label = file ?? d.device ?? "disk";
      return d.device ? `${d.device}: ${label}${size ? ` (${size})` : ""}` : label;
    })
    .join(", ");
}

export function hypervisorPowerLabel(state: string | null | undefined): {
  label: string;
  className: string;
} {
  const s = (state ?? "").toUpperCase();
  if (s === "RUNNING") {
    return { label: "Running", className: "bg-emerald-900/50 text-emerald-300" };
  }
  if (s === "SHUTOFF" || s === "NOSTATE" || s === "") {
    return { label: "Stopped", className: "bg-slate-800 text-slate-400" };
  }
  return { label: state ?? "Unknown", className: "bg-amber-900/40 text-amber-200" };
}

/** Secondary note when guest SSH disagrees with hypervisor (never shown as primary power state). */
export function guestReachabilityNote(
  guestStatus: string | null | undefined,
  libvirtState: string | null | undefined,
): string | null {
  const hypervisor = (libvirtState ?? "").toUpperCase();
  const guest = guestStatus ?? "";
  if (hypervisor === "RUNNING" && (guest === "off" || guest === "degraded")) {
    return "Guest OS not reachable via SSH (hypervisor reports running).";
  }
  if (guest === "on" && guest) return null;
  return null;
}

export function formatVmStatusLine(vm: {
  libvirt_state?: string | null;
  guest_status?: string | null;
  status?: string | null;
  state?: string | null;
  memory_mib?: number | null;
}): string {
  const hypervisor = vm.libvirt_state ?? vm.state ?? "—";
  const guest = vm.guest_status ?? vm.status;
  const parts = [`Hypervisor: ${hypervisor}`];
  if (guest && guest !== "on") {
    parts.push(`Guest SSH: ${guest}`);
  }
  if (vm.memory_mib != null) {
    parts.push(`${vm.memory_mib} MB`);
  }
  return parts.join(" · ");
}
