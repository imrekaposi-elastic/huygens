import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { canManageInfrastructureCompliance } from "@/auth/permissions";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";

type Props = {
  organizationId: string;
  providerId: string;
  regionId?: string;
};

export function InfrastructureCharacteristicsPanel({ organizationId, providerId, regionId }: Props) {
  const { user } = useAuth();
  const platformAdmin = isPlatformAdmin(getAccessToken());
  const canManage = canManageInfrastructureCompliance(user, organizationId, platformAdmin);
  const qc = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const isProvider = !regionId;

  const characteristics = useQuery({
    queryKey: ["grc-characteristics", organizationId],
    queryFn: () => api.listQualitativeCharacteristics(organizationId),
    enabled: !!organizationId,
  });

  const links = useQuery({
    queryKey: ["infra-characteristics", organizationId, providerId, regionId ?? "provider"],
    queryFn: () =>
      isProvider
        ? api.getProviderCharacteristics(organizationId, providerId)
        : api.getRegionCharacteristics(organizationId, regionId!),
    enabled: !!organizationId && (!!providerId || !!regionId),
  });

  const serverIds = useMemo(() => (links.data?.characteristic_ids ?? []).slice().sort().join(","), [links.data]);

  useEffect(() => {
    setSelectedIds(links.data?.characteristic_ids ?? []);
  }, [serverIds]);

  const save = useMutation({
    mutationFn: async () => {
      if (isProvider) {
        await api.setProviderCharacteristics(organizationId, providerId, selectedIds);
        return;
      }
      await api.setRegionCharacteristics(organizationId, regionId!, selectedIds);
    },
    onSuccess: () => {
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["infra-characteristics", organizationId, providerId, regionId ?? "provider"] });
      void qc.invalidateQueries({ queryKey: ["compliance-explorer-facets", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-explorer", organizationId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Save failed"),
  });

  function toggle(id: string) {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  const list = characteristics.data ?? [];

  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-800 dark:bg-slate-900/50">
      <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
        {isProvider ? "Provider qualitative characteristics" : "Region qualitative characteristics"}
      </h3>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        Checked characteristics inherit to agents placed on this {isProvider ? "provider" : "region/sub-region"} and are
        searchable as placement traits in Compliance Explorer.
      </p>

      {!list.length && (
        <p className="text-sm text-slate-500">
          No qualitative characteristics yet — create them under Compliance → GRC.
        </p>
      )}

      <ul className="mb-3 max-h-48 space-y-1 overflow-y-auto text-sm">
        {list.map((ch) => (
          <li key={ch.id}>
            <label
              className={`flex items-start gap-2 rounded border border-slate-200 bg-white px-2 py-1.5 dark:border-slate-700 dark:bg-slate-900 ${
                canManage ? "" : "cursor-default opacity-80"
              }`}
            >
              <input
                type="checkbox"
                className="mt-0.5 accent-emerald-600"
                checked={selectedIds.includes(ch.id)}
                disabled={!canManage || save.isPending}
                onChange={() => toggle(ch.id)}
              />
              <span>
                {ch.name}
                <span className="ml-2 text-xs uppercase text-slate-400">{ch.moscow}</span>
                <span className="ml-2 font-mono text-xs text-slate-500">{ch.slug}</span>
              </span>
            </label>
          </li>
        ))}
      </ul>

      {canManage && list.length > 0 && (
        <button
          type="button"
          disabled={save.isPending}
          onClick={() => save.mutate()}
          className="min-h-9 rounded bg-emerald-600 px-3 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          {save.isPending ? "Saving…" : "Save characteristics"}
        </button>
      )}

      {!canManage && (
        <p className="text-xs text-slate-500">
          Only <strong>admin</strong> and <strong>compliance_admin</strong> can edit infrastructure characteristics.
        </p>
      )}
      {err && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{err}</p>}
    </div>
  );
}

