import { useState } from "react";
import { isValidOrgSlug, slugFromName } from "@/auth/setup";
import { api, ApiError } from "@/api/client";

type Props = {
  open: boolean;
  onClose: () => void;
  onCreated: (orgId: string) => void;
};

export function OrganizationCreateDialog({ open, onClose, onCreated }: Props) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const finalSlug = slug.trim() || slugFromName(name);
    if (!name.trim()) {
      setError("Name is required.");
      return;
    }
    if (!isValidOrgSlug(finalSlug)) {
      setError("Slug must be lowercase letters, numbers, and hyphens (e.g. acme-corp).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const org = await api.createOrganization({ name: name.trim(), slug: finalSlug });
      setName("");
      setSlug("");
      setSlugTouched(false);
      onCreated(org.id);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create organization");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 dark:bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-org-title"
    >
      <form
        onSubmit={submit}
        className="w-full max-w-md rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-6 shadow-xl"
      >
        <h2 id="create-org-title" className="text-lg font-semibold text-slate-900 dark:text-white">
          New organization
        </h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Organizations isolate tenants. Platform admins can create multiple organizations.
        </p>
        {error && (
          <p className="mt-3 rounded bg-red-50/90 dark:bg-red-950/50 px-3 py-2 text-sm text-red-700 dark:text-red-300">{error}</p>
        )}
        <label className="mt-4 block text-sm">
          Name
          <input
            className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (!slugTouched) setSlug(slugFromName(e.target.value));
            }}
            autoFocus
            required
          />
        </label>
        <label className="mt-3 block text-sm">
          URL slug
          <input
            className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
            value={slug}
            onChange={(e) => {
              setSlugTouched(true);
              setSlug(e.target.value);
            }}
            placeholder="acme-corp"
          />
        </label>
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className="min-h-11 rounded-lg border border-slate-300 dark:border-slate-600 px-4 text-sm hover:bg-slate-50 dark:bg-slate-800"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy}
            className="min-h-11 rounded-lg bg-emerald-600 px-5 font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            {busy ? "Creating…" : "Create"}
          </button>
        </div>
      </form>
    </div>
  );
}
