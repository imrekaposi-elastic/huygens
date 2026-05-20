export function formatBytes(n: number, decimals = 1): string {
  if (!Number.isFinite(n) || n < 0) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(decimals)} KB`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(decimals)} MB`;
  return `${(n / 1024 ** 3).toFixed(decimals)} GB`;
}

export function formatRate(bytesPerSec: number | null): string {
  if (bytesPerSec == null || !Number.isFinite(bytesPerSec)) return "—";
  return `${formatBytes(bytesPerSec)}/s`;
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
