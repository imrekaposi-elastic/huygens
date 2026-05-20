/** Background refresh for agent/inventory views (aligns ~with inventory poll). */
export const LIVE_REFETCH_INTERVAL_MS = 15_000;

export const liveQueryOptions = {
  refetchInterval: LIVE_REFETCH_INTERVAL_MS,
  refetchOnWindowFocus: true,
} as const;
