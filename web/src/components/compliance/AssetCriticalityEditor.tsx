import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { AssetCriticality, ComplianceItem } from "@/api/types";
import {
  ComplianceMembershipLegend,
  MembershipCheckbox,
} from "@/components/compliance/ComplianceMembershipLegend";

type Props = {
  organizationId: string;
  title: string;
  description?: string;
  canEdit: boolean;
  queryKey: readonly unknown[];
  load: () => Promise<AssetCriticality>;
  save: (body: { compliance_item_ids: string[]; placement_note?: string }) => Promise<AssetCriticality>;
  onSaveSuccess?: () => void;
};

export function AssetCriticalityEditor({
  organizationId,
  title,
  description,
  canEdit,
  queryKey,
  load,
  save,
  onSaveSuccess,
}: Props) {
  const qc = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [placementNote, setPlacementNote] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const catalog = useQuery({
    queryKey: ["compliance-catalog", organizationId],
    queryFn: () => api.listComplianceCatalog(organizationId),
    enabled: !!organizationId,
  });

  const assignment = useQuery({
    queryKey,
    queryFn: load,
    enabled: !!organizationId,
  });

  const isProject = assignment.data?.resource_type === "project";
  const inheritedItems = assignment.data?.inherited_compliance_items ?? [];
  const aggregateItems = assignment.data?.aggregate_compliance_items ?? [];
  const inheritedIdSet = useMemo(
    () => new Set(inheritedItems.map((i) => i.id)),
    [inheritedItems],
  );
  const aggregateIdSet = useMemo(
    () => new Set(aggregateItems.map((i) => i.id)),
    [aggregateItems],
  );

  const displayItems = useMemo(() => {
    const byId = new Map<string, ComplianceItem>();
    for (const item of catalog.data ?? []) {
      byId.set(item.id, item);
    }
    for (const item of inheritedItems) {
      byId.set(item.id, item);
    }
    for (const item of aggregateItems) {
      byId.set(item.id, item);
    }
    return [...byId.values()].sort((a, b) => a.name.localeCompare(b.name));
  }, [catalog.data, inheritedItems, aggregateItems]);

  useEffect(() => {
    if (!assignment.data) return;
    setSelectedIds(assignment.data.compliance_items.map((i) => i.id));
    setPlacementNote(assignment.data.placement_note ?? "");
  }, [assignment.data]);

  const persist = useMutation({
    mutationFn: () =>
      save({
        compliance_item_ids: selectedIds,
        placement_note: placementNote.trim() || undefined,
      }),
    onSuccess: () => {
      setErr(null);
      void qc.invalidateQueries({ queryKey });
      void qc.invalidateQueries({ queryKey: ["compliance-dashboard", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-explorer", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-explorer-facets", organizationId] });
      onSaveSuccess?.();
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Save failed"),
  });

  function toggleItem(item: ComplianceItem) {
    setSelectedIds((prev) =>
      prev.includes(item.id) ? prev.filter((id) => id !== item.id) : [...prev, item.id],
    );
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">{title}</h2>
      {description && (
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{description}</p>
      )}
      <ComplianceMembershipLegend
        className="mt-3 border-t border-slate-100 pt-3 dark:border-slate-800"
        showAggregate={isProject}
      />
      {assignment.isLoading && <p className="mt-3 text-sm text-slate-500">Loading…</p>}
      {!assignment.isLoading && (
        <div className="mt-4 space-y-4">
          {displayItems.length === 0 ? (
            <p className="text-sm text-amber-700 dark:text-amber-300">
              Add standards in <strong>Compliance → Catalog</strong> before linking them here.
            </p>
          ) : (
            <ul className="space-y-2">
              {displayItems.map((item) => {
                const isDirect = selectedIds.includes(item.id);
                const isInherited = inheritedIdSet.has(item.id);
                const isAggregate = aggregateIdSet.has(item.id);
                const isInheritedOnly = isInherited && !isDirect;
                const isAggregateOnly = isAggregate && !isDirect && !isInherited;

                return (
                  <li key={item.id}>
                    {isAggregateOnly ? (
                      <div className="flex items-start gap-2 rounded-lg border border-blue-200 bg-blue-50/90 p-3 text-sm dark:border-blue-800 dark:bg-blue-950/40">
                        <MembershipCheckbox variant="aggregate" className="mt-0.5" />
                        <span>
                          <span className="font-medium text-blue-900 dark:text-blue-100">
                            {item.name}
                          </span>
                          <span className="ml-2 text-xs uppercase text-blue-600/80 dark:text-blue-400/80">
                            {item.moscow}
                          </span>
                          <span className="mt-0.5 block text-xs text-blue-700/90 dark:text-blue-300/90">
                            All child objects are compliant
                          </span>
                          {item.description && (
                            <span className="mt-0.5 block text-xs text-blue-700/80 dark:text-blue-300/80">
                              {item.description}
                            </span>
                          )}
                        </span>
                      </div>
                    ) : isInheritedOnly ? (
                      <div className="flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50/90 p-3 text-sm dark:border-slate-700 dark:bg-slate-800/60">
                        <MembershipCheckbox variant="inherited" className="mt-0.5" />
                        <span>
                          <span className="font-medium text-slate-700 dark:text-slate-200">
                            {item.name}
                          </span>
                          <span className="ml-2 text-xs uppercase text-slate-400">{item.moscow}</span>
                          <span className="mt-0.5 block text-xs text-slate-500">
                            Inherited from provider or region
                          </span>
                          {item.description && (
                            <span className="mt-0.5 block text-xs text-slate-500">
                              {item.description}
                            </span>
                          )}
                        </span>
                      </div>
                    ) : (
                      <label
                        className={`flex cursor-pointer items-start gap-2 rounded-lg border p-3 text-sm ${
                          isDirect
                            ? "border-emerald-500/60 bg-emerald-50/80 dark:bg-emerald-950/30"
                            : "border-slate-200 dark:border-slate-700"
                        } ${!canEdit ? "cursor-default opacity-90" : ""}`}
                      >
                        <input
                          type="checkbox"
                          className="mt-0.5 accent-emerald-600"
                          checked={isDirect}
                          disabled={!canEdit || persist.isPending}
                          onChange={() => toggleItem(item)}
                        />
                        <span>
                          <span className="font-medium">{item.name}</span>
                          {isInherited && isDirect && (
                            <span className="ml-2 text-xs text-slate-500">(also inherited)</span>
                          )}
                          <span className="ml-2 text-xs uppercase text-slate-500">{item.moscow}</span>
                          {item.description && (
                            <span className="mt-0.5 block text-slate-500">{item.description}</span>
                          )}
                        </span>
                      </label>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
          <label className="block text-sm">
            Placement note (optional)
            <textarea
              className="mt-1 w-full min-h-20 rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 dark:border-slate-700 dark:bg-slate-800"
              value={placementNote}
              onChange={(e) => setPlacementNote(e.target.value)}
              disabled={!canEdit || persist.isPending}
              placeholder="Human rationale for auditors…"
            />
          </label>
          {canEdit && displayItems.length > 0 && (
            <button
              type="button"
              disabled={persist.isPending}
              onClick={() => persist.mutate()}
              className="min-h-10 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
            >
              {persist.isPending ? "Saving…" : "Save assignment"}
            </button>
          )}
          {!canEdit && (
            <p className="text-xs text-slate-500">
              Requires the <strong>compliance_engineer</strong> or <strong>admin</strong> org role to
              edit direct assignments.
            </p>
          )}
        </div>
      )}
      {err && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{err}</p>}
    </section>
  );
}
