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
  onMigrated: () => void | Promise<void>;
};

export function AgentMigrateRegionDialog({ open, agent, onClose, onMigrated }: Props) {
  const [regionId, setRegionId] = useState("");
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

  // Initialize only when dialog opens — do not reset when regionOptions loads (new array each fetch).
  useEffect(() => {
    if (!open || !agent) return;
    setError(null);
    setRegionId(agent.region_id ?? "");
  }, [open, agent?.id, agent?.region_id]);

  useEffect(() => {
    if (!open || !agent || regionId || regionOptions.length === 0) return;
    if (!agent.region_id) setRegionId(regionOptions[0].id);
  }, [open, agent?.id, agent?.region_id, regionId, regionOptions]);

  if (!open || !agent) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!agent) return;
    if (!regionId) {
      setError("Select a target region.");
      return;
    }
    if (regionId === agent.region_id) {
      setError("Agent is already in this region.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await api.patchAgent(agent.id, {
        region_id: regionId,
        infrastructure_provider_id: providerId,
      });
      if (updated.region_id !== regionId) {
        setError("Region was not updated — check registry logs.");
        return;
      }
      await onMigrated();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Migration failed");
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
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Move agent to region</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          <span className="font-mono text-slate-700 dark:text-slate-300">{agent.name}</span> stays on one region
          (libvirt). Child regions under the new node inherit coverage; parent regions become
          operational.
        </p>

        <form onSubmit={submit} className="mt-4 space-y-3">
          {error && (
            <p className="rounded bg-red-50/90 dark:bg-red-950/50 px-3 py-2 text-sm text-red-700 dark:text-red-300">{error}</p>
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
              Target region
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
              {busy ? "Moving…" : "Move"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
