/** Libvirt built-in network — not project-managed (see FRAMEWORK_PLAN / agent readonly). */
export const LIBVIRT_SYSTEM_NETWORK = "default";

export function isSystemNetwork(name: string | null | undefined): boolean {
  return name === LIBVIRT_SYSTEM_NETWORK;
}

export function filterManagedNetworks<T extends { name: string | null }>(networks: T[]): T[] {
  return networks.filter((n) => !isSystemNetwork(n.name));
}

/** Networks that can be attached when creating a VM (includes libvirt default). */
export function networksForVmSelect<T extends { name: string | null; readonly?: boolean }>(
  networks: T[],
): T[] {
  return networks
    .filter((n) => n.name)
    .filter((n) => isSystemNetwork(n.name) || !n.readonly)
    .sort((a, b) => {
      if (a.name === LIBVIRT_SYSTEM_NETWORK) return -1;
      if (b.name === LIBVIRT_SYSTEM_NETWORK) return 1;
      return String(a.name).localeCompare(String(b.name));
    });
}
