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

export function InfrastructureCompliancePanel({
  organizationId,
  providerId,
  regionId,
}: Props) {
  const { user } = useAuth();
  const platformAdmin = isPlatformAdmin(getAccessToken());
  const canManage = canManageInfrastructureCompliance(user, organizationId, platformAdmin);
  const qc = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);

  const isProvider = !regionId;
  const catalog = useQuery({
    queryKey: ["compliance-catalog", organizationId],
    queryFn: () => api.listComplianceCatalog(organizationId),
    enabled: !!organizationId,
  });

  const providerProfile = useQuery({
    queryKey: ["provider-compliance", organizationId, providerId],
    queryFn: () => api.getProviderComplianceProfile(organizationId, providerId),
    enabled: isProvider && !!organizationId,
  });

  const regionProfile = useQuery({
    queryKey: ["region-compliance", organizationId, regionId],
    queryFn: () => api.getRegionComplianceItems(organizationId, regionId!),
    enabled: !isProvider && !!regionId && !!organizationId,
  });

  const serverItemIds = useMemo(() => {
    const items = isProvider
      ? (providerProfile.data?.compliance_items ?? [])
      : (regionProfile.data?.compliance_items ?? []);
    return items
      .map((i) => i.id)
      .sort()
      .join(",");
  }, [isProvider, providerProfile.data, regionProfile.data]);

  useEffect(() => {
    if (isProvider) {
      if (!providerProfile.data) return;
      setSelectedIds(providerProfile.data.compliance_items.map((i) => i.id));
      return;
    }
    if (!regionProfile.data) return;
    setSelectedIds(regionProfile.data.compliance_items.map((i) => i.id));
  }, [serverItemIds, isProvider, providerProfile.data, regionProfile.data]);

  const save = useMutation({
    mutationFn: async () => {
      if (isProvider) {
        await api.setProviderComplianceProfile(organizationId, providerId, {
          compliance_item_ids: selectedIds,
        });
        return;
      }
      await api.setRegionComplianceItems(organizationId, regionId!, {
        compliance_item_ids: selectedIds,
      });
    },
    onSuccess: () => {
      setErr(null);
      if (isProvider) {
        void qc.invalidateQueries({
          queryKey: ["provider-compliance", organizationId, providerId],
        });
      } else {
        void qc.invalidateQueries({
          queryKey: ["region-compliance", organizationId, regionId],
        });
      }
      void qc.invalidateQueries({ queryKey: ["compliance-dashboard", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-explorer-facets", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-explorer", organizationId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Save failed"),
  });

  function toggleItem(id: string) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  const catalogItems = catalog.data ?? [];

  if (!organizationId) {
    return (
      <p className="mt-4 text-sm text-amber-700 dark:text-amber-300">
        Select an organization in the header to configure infrastructure compliance.
      </p>
    );
  }

  return (
    <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-800 dark:bg-slate-900/50">
      <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
        {isProvider ? "Provider compliance" : "Region compliance standards"}
      </h3>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        Checked standards apply to this {isProvider ? "provider" : "region"} and inherit to every
        VM/network on agents placed in this {isProvider ? "provider" : "region or any sub-region"}
        (grey membership in Explorer and resource compliance).
      </p>

      {!catalogItems.length && (
        <p className="text-sm text-slate-500">No catalog items yet — add them under Compliance.</p>
      )}

      <ul className="mb-3 max-h-48 space-y-1 overflow-y-auto text-sm">
        {catalogItems.map((item) => (
          <li key={item.id}>
            <label
              className={`flex cursor-pointer items-start gap-2 rounded border border-slate-200 bg-white px-2 py-1.5 dark:border-slate-700 dark:bg-slate-900 ${
                canManage ? "" : "cursor-default opacity-80"
              }`}
            >
              <input
                type="checkbox"
                className="mt-0.5 accent-emerald-600"
                checked={selectedIds.includes(item.id)}
                disabled={!canManage || save.isPending}
                onChange={() => toggleItem(item.id)}
              />
              <span>
                {item.name}
                <span className="ml-2 text-xs uppercase text-slate-400">{item.moscow}</span>
              </span>
            </label>
          </li>
        ))}
      </ul>

      {canManage && catalogItems.length > 0 && (
        <button
          type="button"
          disabled={save.isPending}
          onClick={() => save.mutate()}
          className="min-h-9 rounded bg-emerald-600 px-3 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
        >
          {save.isPending ? "Saving…" : "Save standards"}
        </button>
      )}

      {!canManage && (
        <p className="text-xs text-slate-500">
          Only <strong>admin</strong> and <strong>compliance_admin</strong> can edit infrastructure
          compliance.
        </p>
      )}
      {err && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{err}</p>}
    </div>
  );
}
