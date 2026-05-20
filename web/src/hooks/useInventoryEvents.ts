import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { fetchEventSource } from "@microsoft/fetch-event-source";
import { getAccessToken } from "@/auth/token";
import type { InventoryCloudEvent } from "@/api/types";

/**
 * Live inventory via fetch-based SSE + Authorization header.
 * Do NOT use native EventSource (cannot set Bearer; invites ?token= anti-pattern).
 */
export function useInventoryEvents(orgId: string | null, enabled: boolean) {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!enabled || !orgId) return;
    const token = getAccessToken();
    if (!token) return;

    const ctrl = new AbortController();

    void fetchEventSource("/api/v1/inventory/events/stream", {
      signal: ctrl.signal,
      headers: { Authorization: `Bearer ${token}` },
      async onopen(res) {
        if (res.ok && res.headers.get("content-type")?.includes("text/event-stream")) {
          return;
        }
        throw new Error(`SSE failed: ${res.status}`);
      },
      onmessage(ev) {
        if (!ev.data) return;
        try {
          const envelope = JSON.parse(ev.data) as InventoryCloudEvent;
          if (envelope.data?.organization_id !== orgId) return;
          void queryClient.invalidateQueries({ queryKey: ["dashboard", orgId] });
          void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
          void queryClient.invalidateQueries({ queryKey: ["inventory-agents"] });
          // Projects tabs proxy the agent directly — refresh VM/network lists too.
          void queryClient.invalidateQueries({ queryKey: ["vms"] });
          void queryClient.invalidateQueries({ queryKey: ["networks"] });
        } catch {
          /* ignore malformed */
        }
      },
      onerror(err) {
        console.warn("inventory SSE error", err);
      },
    });

    return () => ctrl.abort();
  }, [orgId, enabled, queryClient]);
}
