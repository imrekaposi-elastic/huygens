import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { AgentOut } from "@/api/types";
import { CloudIcon, GlobeIcon } from "@/components/icons/NavIcons";
import { flattenRegionTree } from "@/lib/regionTree";

type Props = {
  open: boolean;
  agent: AgentOut | null;
  onClose: () => void;
  onSaved: (message: string) => void | Promise<void>;
};

export function AgentEditDialog({ open, agent, onClose, onSaved }: Props) {
  const [baseUrl, setBaseUrl] = useState("");
  const [regionId, setRegionId] = useState("");
  const [tlsVerify, setTlsVerify] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const providerId = agent?.infrastructure_provider_id ?? "";

  const { data: providerDetail } = useQuery({
    queryKey: ["infrastructure-provider", providerId],
    queryFn: () => api.infrastructureProvider(providerId),
    enabled: open && !!providerId,
  });

  const regionOptions = useMemo(
    () => (providerDetail ? flattenRegionTree(providerDetail.region_tree) : []),
    [providerDetail],
  );

  useEffect(() => {
    if (!open || !agent) return;
    setError(null);
    setBaseUrl(agent.base_url);
    setRegionId(agent.region_id ?? "");
    setTlsVerify(agent.tls_verify !== false);
  }, [open, agent?.id, agent?.base_url, agent?.region_id, agent?.tls_verify]);

  useEffect(() => {
    if (!open || !agent || regionId || regionOptions.length === 0) return;
    if (!agent.region_id) setRegionId(regionOptions[0].id);
  }, [open, agent?.id, agent?.region_id, regionId, regionOptions]);

  if (!open || !agent) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!agent) return;

    const trimmedUrl = baseUrl.trim();
    if (!trimmedUrl) {
      setError("Base URL is required.");
      return;
    }
    if (!regionId) {
      setError("Select a region.");
      return;
    }

    const body: {
      base_url?: string;
      region_id?: string;
      infrastructure_provider_id?: string;
      tls_verify?: boolean;
    } = {};

    if (trimmedUrl !== agent.base_url) {
      body.base_url = trimmedUrl;
    }
    if (regionId !== (agent.region_id ?? "")) {
      body.region_id = regionId;
      body.infrastructure_provider_id = providerId;
    }
    if (tlsVerify !== (agent.tls_verify !== false)) {
      body.tls_verify = tlsVerify;
    }

    if (Object.keys(body).length === 0) {
      onClose();
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await api.patchAgent(agent.id, body);
      try {
        await api.testAgentConnection(agent.id);
      } catch {
        // Save succeeded; connection test failure is reflected in agent status after refresh.
      }
      await onSaved(`Updated "${agent.name}".`);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 dark:bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className="w-full max-w-md rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Edit agent</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          <span className="font-mono text-slate-700 dark:text-slate-300">{agent.name}</span> — libvirt
          agents cover one region; child regions inherit coverage from the parent node.
        </p>

        <form onSubmit={submit} className="mt-4 space-y-3">
          {error && (
            <p className="rounded bg-red-50/90 dark:bg-red-950/50 px-3 py-2 text-sm text-red-700 dark:text-red-300">
              {error}
            </p>
          )}
          <label className="block text-sm text-slate-600 dark:text-slate-400">
            <span className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
              <CloudIcon className="size-4 shrink-0" />
              Provider
            </span>
            <span className="mt-1 block font-medium text-slate-800 dark:text-slate-200">
              {providerDetail?.name ?? providerId}
            </span>
          </label>
          <label className="block text-sm">
            <span className="mb-1 flex items-center gap-2 text-slate-700 dark:text-slate-300">
              <GlobeIcon className="size-4 shrink-0 text-slate-500 dark:text-slate-500" />
              Region
            </span>
            <select
              className="w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
              value={regionId}
              onChange={(e) => setRegionId(e.target.value)}
              disabled={!regionOptions.length}
            >
              {regionOptions.length === 0 ? (
                <option value="">No regions — create under Infrastructure</option>
              ) : (
                regionOptions.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.label}
                  </option>
                ))
              )}
            </select>
          </label>
          <label className="block text-sm">
            <span className="mb-1 text-slate-700 dark:text-slate-300">Base URL</span>
            <input
              className="w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="https://host.example:8765"
              required
            />
            <span className="mt-1 block text-xs text-slate-500 dark:text-slate-500">
              Libvirt agent HTTPS endpoint (typically port 8765).
            </span>
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={tlsVerify}
              onChange={(e) => setTlsVerify(e.target.checked)}
              className="size-4 rounded border-slate-300 dark:border-slate-600"
            />
            Verify TLS certificate
          </label>
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="min-h-11 rounded-lg border border-slate-300 dark:border-slate-600 px-4 text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={busy || !regionOptions.length}
              className="min-h-11 rounded-lg bg-emerald-600 px-5 font-medium hover:bg-emerald-500 disabled:opacity-50"
            >
              {busy ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
