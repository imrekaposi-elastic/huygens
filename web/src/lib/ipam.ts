/** Client-side subnet sizing (mirrors services/projects ipam/core.py). */

export function hostsToPrefixLen(hosts: number): number {
  if (hosts < 1) return 30;
  const need = hosts + 2;
  const hostBits = Math.max(2, Math.ceil(Math.log2(need)));
  return 32 - hostBits;
}

export function subnetMaskLabel(hosts: number): string {
  return `/${hostsToPrefixLen(hosts)}`;
}

export function addressesInSubnet(prefixLen: number): number {
  return Math.max(0, 2 ** (32 - prefixLen) - 2);
}
