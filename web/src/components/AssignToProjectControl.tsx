import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { api, ApiError } from "@/api/client";

type Props = {
  organizationId: string;
  agentId: string;
  resourceType: "vm" | "network";
  resourceName: string;
  onAssigned?: () => void;
};

export function AssignToProjectControl({
  organizationId,
  agentId,
  resourceType,
  resourceName,
  onAssigned,
}: Props) {
  const qc = useQueryClient();
  const [projectId, setProjectId] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects", organizationId],
    queryFn: () => api.projects(organizationId),
  });

  const assign = useMutation({
    mutationFn: () =>
      api.assignResourceToProject(projectId, agentId, {
        resource_type: resourceType,
        name: resourceName,
      }),
    onSuccess: () => {
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["dashboard", organizationId] });
      onAssigned?.();
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Assign failed"),
  });

  if (isLoading) {
    return <span className="text-xs text-slate-500">Loading projects…</span>;
  }

  if (!projects?.length) {
    return (
      <Link to="/projects" className="text-xs text-amber-200 underline">
        Create a project first
      </Link>
    );
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap items-center justify-end gap-1">
        <select
          className="max-w-[10rem] rounded border border-slate-600 bg-slate-800 px-2 py-1 text-xs"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
          aria-label={`Project for ${resourceName}`}
        >
          <option value="">Assign to…</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={!projectId || assign.isPending}
          onClick={() => assign.mutate()}
          className="rounded border border-emerald-800 bg-emerald-950/50 px-2 py-1 text-xs font-medium text-emerald-200 hover:bg-emerald-950 disabled:opacity-50"
        >
          {assign.isPending ? "Assigning…" : "Assign"}
        </button>
      </div>
      {err && <p className="max-w-[14rem] text-right text-xs text-red-300">{err}</p>}
    </div>
  );
}
