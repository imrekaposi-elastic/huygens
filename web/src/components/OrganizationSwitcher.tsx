import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import { api, ApiError } from "@/api/client";
import { OrganizationCreateDialog } from "@/components/OrganizationCreateDialog";
export function OrganizationSwitcher() {
  const navigate = useNavigate();
  const { organizations, selectedOrgId, setSelectedOrgId, refresh } = useAuth();
  const isAdmin = isPlatformAdmin(getAccessToken());
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = organizations.find((o) => o.id === selectedOrgId);

  async function handleDelete() {
    if (!selectedOrgId || !selected) return;
    const ok = window.confirm(
      `Delete organization "${selected.name}" (${selected.slug})?\n\n` +
        "IAM memberships and mappings for this org will be removed. " +
        "Delete all projects in this org first.",
    );
    if (!ok) return;
    setError(null);
    setDeleteBusy(true);
    try {
      const projects = await api.projects(selectedOrgId);
      if (projects.length > 0) {
        setError(`Delete ${projects.length} project(s) in this organization before removing it.`);
        return;
      }
      await api.deleteOrganization(selectedOrgId);
      await refresh();
      const remaining = await api.organizations();
      if (remaining.length === 0 && isPlatformAdmin(getAccessToken())) {
        void navigate({ to: "/setup", replace: true });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed");
    } finally {
      setDeleteBusy(false);
    }
  }

  function onCreated(orgId: string) {
    void refresh().then(() => setSelectedOrgId(orgId));
  }

  if (organizations.length === 0 && isAdmin) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-slate-600 dark:text-slate-400">No organizations yet</span>
        <button
          type="button"
          onClick={() => void navigate({ to: "/setup" })}
          className="min-h-11 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500"
        >
          Run setup wizard
        </button>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          className="min-h-11 rounded-lg border border-slate-300 dark:border-slate-600 px-4 text-sm hover:bg-slate-50 dark:bg-slate-800"
        >
          New organization
        </button>
        <OrganizationCreateDialog
          open={createOpen}
          onClose={() => setCreateOpen(false)}
          onCreated={onCreated}
        />
      </div>
    );
  }

  if (organizations.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="text-sm text-slate-600 dark:text-slate-400">
        Organization
        <select
          className="ml-2 min-h-11 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-2 text-sm text-slate-900 dark:text-white"
          value={selectedOrgId ?? ""}
          onChange={(e) => setSelectedOrgId(e.target.value)}
        >
          {organizations.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </select>
      </label>
      {isAdmin && (
        <>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="min-h-11 rounded-lg border border-slate-300 dark:border-slate-600 px-3 text-sm hover:bg-slate-50 dark:bg-slate-800"
          >
            New
          </button>
          <button
            type="button"
            onClick={() => void handleDelete()}
            disabled={!selectedOrgId || deleteBusy}
            className="min-h-11 rounded-lg border border-red-300 dark:border-red-900/80 px-3 text-sm text-red-700 dark:text-red-300 hover:bg-red-50 dark:bg-red-950/40 disabled:opacity-40"
          >
            {deleteBusy ? "Deleting…" : "Delete"}
          </button>
        </>
      )}
      {error && <p className="w-full text-sm text-red-600 dark:text-red-400">{error}</p>}
      <OrganizationCreateDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={onCreated}
      />
    </div>
  );
}
