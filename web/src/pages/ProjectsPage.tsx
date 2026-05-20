import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthContext";
import { api, ApiError } from "@/api/client";

export function ProjectsPage() {
  const { selectedOrgId } = useAuth();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["projects", selectedOrgId],
    queryFn: () => api.projects(selectedOrgId ?? undefined),
    enabled: !!selectedOrgId,
  });

  const create = useMutation({
    mutationFn: () =>
      api.createProject({
        organization_id: selectedOrgId!,
        name,
        slug: slug || name.toLowerCase().replace(/\s+/g, "-"),
      }),
    onSuccess: () => {
      setName("");
      setSlug("");
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["projects", selectedOrgId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Create failed"),
  });

  if (!selectedOrgId) return <p className="text-slate-400">Select an organization</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Projects</h1>
      <form
        className="flex flex-col gap-3 rounded-lg border border-slate-800 bg-slate-900 p-4 md:flex-row md:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <label className="flex-1 text-sm">
          Name
          <input
            className="mt-1 w-full min-h-11 rounded border border-slate-700 bg-slate-800 px-3"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </label>
        <label className="flex-1 text-sm">
          Slug
          <input
            className="mt-1 w-full min-h-11 rounded border border-slate-700 bg-slate-800 px-3"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
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
      {err && <p className="text-sm text-red-400">{err}</p>}
      {isLoading && <p className="text-slate-400">Loading…</p>}
      <ul className="space-y-2">
        {data?.map((p) => (
          <li key={p.id}>
            <Link
              to="/projects/$projectId"
              params={{ projectId: p.id }}
              className="block rounded-lg border border-slate-800 bg-slate-900 p-4 hover:border-emerald-800"
            >
              <span className="font-medium">{p.name}</span>
              <span className="ml-2 text-sm text-slate-500">{p.slug}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
