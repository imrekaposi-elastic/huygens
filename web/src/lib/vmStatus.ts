/** VM status from libvirt agent: hypervisor state vs SSH guest probe. */

export function formatVmStatusLine(vm: {
  libvirt_state?: string | null;
  guest_status?: string | null;
  status?: string | null;
  state?: string | null;
  memory_mib?: number | null;
}): string {
  const hypervisor = vm.libvirt_state ?? vm.state ?? "—";
  const guest = vm.guest_status ?? (vm.status && vm.status !== hypervisor ? vm.status : null);
  const parts = [`Hypervisor: ${hypervisor}`];
  if (guest) {
    parts.push(`Guest SSH: ${guest}`);
  }
  if (vm.memory_mib != null) {
    parts.push(`${vm.memory_mib} MiB`);
  }
  return parts.join(" · ");
}

export function guestStatusHint(guestStatus: string | null | undefined): string | null {
  if (guestStatus === "off" || guestStatus === "degraded") {
    return "Guest SSH probe failed or VM has no reachable IP — hypervisor state may still be RUNNING.";
  }
  return null;
}
