import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { FolderIcon, FolderOpenIcon, PageTitle } from "@/components/icons/NavIcons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthContext";
import { slugFromName } from "@/auth/setup";
import { api, ApiError } from "@/api/client";

export function ProjectsPage() {
  const { selectedOrgId } = useAuth();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["projects", selectedOrgId],
    queryFn: () => api.projects(selectedOrgId ?? undefined),
    enabled: !!selectedOrgId,
  });

  const create = useMutation({
    mutationFn: () =>
      api.createProject({
        organization_id: selectedOrgId!,
        name: name.trim(),
        slug: slug.trim() || slugFromName(name),
      }),
    onSuccess: () => {
      setName("");
      setSlug("");
      setSlugTouched(false);
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["projects", selectedOrgId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Create failed"),
  });

  async function handleDelete(projectId: string, projectName: string) {
    if (
      !window.confirm(
        `Delete project "${projectName}"?\n\nProject resources in the database will be removed.`,
      )
    ) {
      return;
    }
    setErr(null);
    setDeletingId(projectId);
    try {
      await api.deleteProject(projectId);
      void qc.invalidateQueries({ queryKey: ["projects", selectedOrgId] });
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  if (!selectedOrgId) return <p className="text-slate-600 dark:text-slate-400">Select an organization</p>;

  return (
    <div className="space-y-6">
      <PageTitle icon={<FolderIcon />}>Projects</PageTitle>
      <form
        className="flex flex-col gap-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 md:flex-row md:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <label className="flex-1 text-sm">
          Name
          <input
            className="mt-1 w-full min-h-11 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (!slugTouched) setSlug(slugFromName(e.target.value));
            }}
            required
          />
        </label>
        <label className="flex-1 text-sm">
          Slug
          <input
            className="mt-1 w-full min-h-11 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
            value={slug}
            onChange={(e) => {
              setSlugTouched(true);
              setSlug(e.target.value);
            }}
            placeholder="auto from name"
          />
        </label>
        <button
          type="submit"
          disabled={create.isPending}
          className="min-h-11 rounded-lg bg-emerald-600 px-4 font-medium hover:bg-emerald-500"
        >
          Create
        </button>
      </form>
      {err && <p className="text-sm text-red-600 dark:text-red-400">{err}</p>}
      {isLoading && <p className="text-slate-600 dark:text-slate-400">Loading…</p>}
      <ul className="space-y-2">
        {data?.map((p) => (
          <li
            key={p.id}
            className="flex items-center gap-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4"
          >
            <Link
              to="/projects/$projectId/vms"
              params={{ projectId: p.id }}
              className="flex min-w-0 flex-1 items-center gap-2 hover:text-emerald-600 dark:text-emerald-400"
            >
              <FolderOpenIcon className="size-5 shrink-0 text-amber-700 dark:text-amber-400/90" />
              <span className="min-w-0">
                <span className="font-medium">{p.name}</span>
                <span className="ml-2 text-sm text-slate-500 dark:text-slate-500">{p.slug}</span>
              </span>
            </Link>
            <button
              type="button"
              onClick={() => void handleDelete(p.id, p.name)}
              disabled={deletingId === p.id}
              className="shrink-0 min-h-11 rounded-lg border border-red-300 dark:border-red-900/80 px-3 text-sm text-red-700 dark:text-red-300 hover:bg-red-50 dark:bg-red-950/40 disabled:opacity-50"
            >
              {deletingId === p.id ? "Deleting…" : "Delete"}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
