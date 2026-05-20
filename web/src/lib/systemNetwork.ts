/** Libvirt built-in network — not project-managed (see FRAMEWORK_PLAN / agent readonly). */
export const LIBVIRT_SYSTEM_NETWORK = "default";

export function isSystemNetwork(name: string | null | undefined): boolean {
  return name === LIBVIRT_SYSTEM_NETWORK;
}

export function filterManagedNetworks<T extends { name: string | null }>(networks: T[]): T[] {
  return networks.filter((n) => !isSystemNetwork(n.name));
}
