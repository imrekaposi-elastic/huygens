export function formatBytes(n: number, decimals = 1): string {
  if (!Number.isFinite(n) || n < 0) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(decimals)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(decimals)} MB`;
  return `${(n / 1024 ** 3).toFixed(decimals)} GB`;
}

/** Bytes per second → megabits per second (decimal Mbps, 1 Mb = 10⁶ bits). */
export function bytesPerSecToMbps(bytesPerSec: number): number {
  return (bytesPerSec * 8) / 1_000_000;
}

export function formatMegabitsPerSec(bytesPerSec: number | null, decimals = 2): string {
  if (bytesPerSec == null || !Number.isFinite(bytesPerSec)) return "—";
  const mbps = bytesPerSecToMbps(bytesPerSec);
  if (mbps >= 1000) return `${(mbps / 1000).toFixed(decimals)} Gbps`;
  if (mbps >= 1) return `${mbps.toFixed(decimals)} Mbps`;
  if (mbps >= 0.001) return `${(mbps * 1000).toFixed(decimals)} Kbps`;
  return `${(bytesPerSec * 8).toFixed(0)} bps`;
}

export function formatIops(opsPerSec: number | null): string {
  if (opsPerSec == null || !Number.isFinite(opsPerSec)) return "—";
  if (opsPerSec >= 1000) return `${(opsPerSec / 1000).toFixed(1)}k/s`;
  return `${Math.round(opsPerSec)}/s`;
}

export function formatPercent(n: number): string {
  if (!Number.isFinite(n)) return "—";
  return `${n.toFixed(1)}%`;
}
