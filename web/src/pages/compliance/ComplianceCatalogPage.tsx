import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { ComplianceItem, MoscowKind } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { canManageComplianceCatalog } from "@/auth/permissions";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";

const MOSCOW_OPTIONS: MoscowKind[] = ["must", "should", "could", "wont"];

function CatalogItemRow({
  item,
  canManage,
  organizationId,
  onError,
}: {
  item: ComplianceItem;
  canManage: boolean;
  organizationId: string;
  onError: (msg: string) => void;
}) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(item.name);
  const [moscow, setMoscow] = useState<MoscowKind>(item.moscow);
  const [targetLevel, setTargetLevel] = useState(item.target_level ?? "");
  const [description, setDescription] = useState(item.description ?? "");

  const updateItem = useMutation({
    mutationFn: () =>
      api.updateComplianceCatalogItem(organizationId, item.id, {
        name: name.trim(),
        moscow,
        target_level: targetLevel.trim() || null,
        description: description.trim() || null,
      }),
    onSuccess: () => {
      setEditing(false);
      void qc.invalidateQueries({ queryKey: ["compliance-catalog", organizationId] });
    },
    onError: (e) => onError(e instanceof ApiError ? e.message : "Update failed"),
  });

  const removeItem = useMutation({
    mutationFn: () => api.deleteComplianceCatalogItem(organizationId, item.id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["compliance-catalog", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-dashboard", organizationId] });
    },
    onError: (e) => onError(e instanceof ApiError ? e.message : "Delete failed"),
  });

  if (editing) {
    return (
      <li className="space-y-2 rounded-lg border border-emerald-500/40 bg-emerald-50/50 p-3 dark:bg-emerald-950/20">
        <label className="block text-sm">
          Name
          <input
            className="mt-1 w-full min-h-9 rounded border border-slate-300 px-2 dark:border-slate-700 dark:bg-slate-800"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          MoSCoW
          <select
            className="mt-1 w-full min-h-9 rounded border border-slate-300 px-2 dark:border-slate-700 dark:bg-slate-800"
            value={moscow}
            onChange={(e) => setMoscow(e.target.value as MoscowKind)}
          >
            {MOSCOW_OPTIONS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          Target level
          <input
            className="mt-1 w-full min-h-9 rounded border border-slate-300 px-2 dark:border-slate-700 dark:bg-slate-800"
            value={targetLevel}
            onChange={(e) => setTargetLevel(e.target.value)}
            placeholder="e.g. high, critical"
          />
        </label>
        <label className="block text-sm">
          Description
          <textarea
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1 dark:border-slate-700 dark:bg-slate-800"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
          />
        </label>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={updateItem.isPending}
            onClick={() => updateItem.mutate()}
            className="rounded bg-emerald-600 px-3 py-1.5 text-sm font-medium hover:bg-emerald-500"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="rounded border border-slate-300 px-3 py-1.5 text-sm dark:border-slate-600"
          >
            Cancel
          </button>
        </div>
      </li>
    );
  }

  return (
    <li className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
      <span>
        <span className="font-medium">{item.name}</span>
        <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-xs uppercase dark:bg-slate-800">
          {item.moscow}
        </span>
        {item.target_level && (
          <span className="ml-1 text-xs text-slate-500">· {item.target_level}</span>
        )}
        {item.description && (
          <span className="mt-0.5 block text-xs text-slate-500">{item.description}</span>
        )}
      </span>
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-slate-500">{item.slug}</span>
        {canManage && (
          <>
            <button
              type="button"
              className="text-xs text-emerald-700 hover:underline dark:text-emerald-300"
              onClick={() => setEditing(true)}
            >
              Edit
            </button>
            <button
              type="button"
              className="text-xs text-red-600 hover:underline dark:text-red-400"
              disabled={removeItem.isPending}
              onClick={() => {
                if (window.confirm(`Delete catalog item "${item.name}"?`)) removeItem.mutate();
              }}
            >
              Delete
            </button>
          </>
        )}
      </div>
    </li>
  );
}

export function ComplianceCatalogPage() {
  const { user, selectedOrgId } = useAuth();
  const organizationId = selectedOrgId ?? "";
  const platformAdmin = isPlatformAdmin(getAccessToken());
  const canManage = canManageComplianceCatalog(user, organizationId, platformAdmin);
  const qc = useQueryClient();
  const [err, setErr] = useState<string | null>(null);
  const [itemName, setItemName] = useState("");
  const [itemMoscow, setItemMoscow] = useState<MoscowKind>("should");

  const catalog = useQuery({
    queryKey: ["compliance-catalog", organizationId],
    queryFn: () => api.listComplianceCatalog(organizationId),
  });

  const createItem = useMutation({
    mutationFn: () =>
      api.createComplianceCatalogItem(organizationId, {
        name: itemName.trim(),
        moscow: itemMoscow,
      }),
    onSuccess: () => {
      setItemName("");
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["compliance-catalog", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-dashboard", organizationId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Create failed"),
  });

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <h2 className="mb-1 text-lg font-medium text-slate-800 dark:text-slate-100">Catalog</h2>
      <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
        Org-wide compliance standards (BIO, ISO, residency, etc.). Link them to projects, VMs,
        networks, or infrastructure regions.
      </p>
      {!canManage && (
        <p className="mb-3 text-xs text-slate-500">
          Edit and delete require <strong>admin</strong> or <strong>compliance_admin</strong>.
        </p>
      )}
      {catalog.isLoading && <p className="text-sm text-slate-500">Loading…</p>}
      <ul className="mb-4 divide-y divide-slate-100 dark:divide-slate-800">
        {(catalog.data ?? []).map((item) => (
          <CatalogItemRow
            key={item.id}
            item={item}
            canManage={canManage}
            organizationId={organizationId}
            onError={setErr}
          />
        ))}
      </ul>
      {canManage && (
        <form
          className="flex flex-col gap-3 md:flex-row md:items-end"
          onSubmit={(e) => {
            e.preventDefault();
            createItem.mutate();
          }}
        >
          <label className="flex-1 text-sm">
            New standard
            <input
              className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 dark:border-slate-700 dark:bg-slate-800"
              value={itemName}
              onChange={(e) => setItemName(e.target.value)}
              required
            />
          </label>
          <label className="text-sm">
            MoSCoW
            <select
              className="mt-1 block min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 dark:border-slate-700 dark:bg-slate-800"
              value={itemMoscow}
              onChange={(e) => setItemMoscow(e.target.value as MoscowKind)}
            >
              {MOSCOW_OPTIONS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={createItem.isPending}
            className="min-h-10 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500"
          >
            Add
          </button>
        </form>
      )}
      {err && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{err}</p>}
    </section>
  );
}
