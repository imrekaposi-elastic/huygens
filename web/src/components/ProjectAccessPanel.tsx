import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthContext";
import { api, ApiError } from "@/api/client";
import { PROJECT_ROLES } from "@/lib/rbac";

type Props = {
  /** When set, only manage access for this workspace (project). */
  projectId?: string;
  projectName?: string;
};

export function ProjectAccessPanel({ projectId, projectName }: Props) {
  const { selectedOrgId } = useAuth();
  const qc = useQueryClient();
  const [err, setErr] = useState<string | null>(null);
  const [assignUserId, setAssignUserId] = useState("");
  const [assignProjectId, setAssignProjectId] = useState(projectId ?? "");
  const [assignRole, setAssignRole] = useState<string>(PROJECT_ROLES[0]);

  useEffect(() => {
    if (projectId) setAssignProjectId(projectId);
  }, [projectId]);

  const { data: users, isLoading: usersLoading } = useQuery({
    queryKey: ["admin", "users", selectedOrgId],
    queryFn: () => api.orgUsers(selectedOrgId!),
    enabled: !!selectedOrgId,
  });

  const { data: projects } = useQuery({
    queryKey: ["projects", selectedOrgId],
    queryFn: () => api.projects(selectedOrgId!),
    enabled: !!selectedOrgId,
  });

  const assign = useMutation({
    mutationFn: () =>
      api.assignProjectRole(selectedOrgId!, assignUserId, {
        project_id: assignProjectId,
        role: assignRole,
      }),
    onSuccess: () => {
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["admin", "users", selectedOrgId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Assign failed"),
  });

  const revoke = useMutation({
    mutationFn: (args: { userId: string; projectId: string; role: string }) =>
      api.revokeProjectRole(selectedOrgId!, args.userId, args.projectId, args.role),
    onSuccess: () => {
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["admin", "users", selectedOrgId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Revoke failed"),
  });

  if (!selectedOrgId) return <p className="text-slate-600 dark:text-slate-400">Select an organization</p>;

  const projectMap = new Map((projects ?? []).map((p) => [p.id, p]));
  const rows: {
    userId: string;
    username: string;
    display: string;
    projectId: string;
    projectLabel: string;
    role: string;
  }[] = [];

  for (const u of users ?? []) {
    for (const pr of u.project_roles.filter((p) => p.organization_id === selectedOrgId)) {
      if (projectId && pr.project_id !== projectId) continue;
      const proj = projectMap.get(pr.project_id);
      rows.push({
        userId: u.id,
        username: u.username,
        display: u.display_name || u.username,
        projectId: pr.project_id,
        projectLabel: proj?.name ?? pr.project_id,
        role: pr.role,
      });
    }
  }
  rows.sort((a, b) => a.projectLabel.localeCompare(b.projectLabel) || a.username.localeCompare(b.username));

  const usersInOrg = users ?? [];

  return (
    <section className="space-y-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/80 p-4">
      <div>
        <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">
          {projectName ? `Access — ${projectName}` : "Project access (per workspace)"}
        </h2>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
          Grant roles per project so users only see and operate that workspace. Org-wide{" "}
          <span className="font-mono">admin</span> still sees all projects. Typical roles:{" "}
          <span className="font-mono">project_admin</span>,{" "}
          <span className="font-mono">operator</span>,{" "}
          <span className="font-mono">auditor</span>.
        </p>
      </div>

      <form
        className="flex flex-wrap items-end gap-3 border-t border-slate-200 dark:border-slate-800 pt-4"
        onSubmit={(e) => {
          e.preventDefault();
          assign.mutate();
        }}
      >
        <label className="text-sm">
          User
          <select
            required
            className="mt-1 block min-h-11 min-w-[10rem] rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-2"
            value={assignUserId}
            onChange={(e) => setAssignUserId(e.target.value)}
          >
            <option value="">Select user…</option>
            {usersInOrg.map((u) => (
              <option key={u.id} value={u.id}>
                {u.display_name || u.username}
              </option>
            ))}
          </select>
        </label>
        {!projectId && (
          <label className="text-sm">
            Project
            <select
              required
              className="mt-1 block min-h-11 min-w-[10rem] rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-2"
              value={assignProjectId}
              onChange={(e) => setAssignProjectId(e.target.value)}
            >
              <option value="">Select project…</option>
              {(projects ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="text-sm">
          Role
          <select
            className="mt-1 block min-h-11 min-w-[11rem] rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-2 font-mono text-xs"
            value={assignRole}
            onChange={(e) => setAssignRole(e.target.value)}
          >
            {PROJECT_ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          disabled={assign.isPending || !assignUserId || !assignProjectId}
          className="min-h-11 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
        >
          {assign.isPending ? "Granting…" : "Grant access"}
        </button>
      </form>

      {err && <p className="text-sm text-red-600 dark:text-red-400">{err}</p>}
      {usersLoading && <p className="text-sm text-slate-500 dark:text-slate-500">Loading…</p>}

      {rows.length === 0 && !usersLoading ? (
        <p className="text-sm text-slate-500 dark:text-slate-500">No project-level grants yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[28rem] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-300 dark:border-slate-700 text-slate-500 dark:text-slate-500">
                {!projectId && <th className="py-2 pr-4">Project</th>}
                <th className="py-2 pr-4">User</th>
                <th className="py-2 pr-4">Role</th>
                <th className="py-2 w-24" />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.userId}-${row.projectId}-${row.role}`} className="border-b border-slate-200 dark:border-slate-800/80">
                  {!projectId && (
                    <td className="py-2 pr-4 text-slate-800 dark:text-slate-200">{row.projectLabel}</td>
                  )}
                  <td className="py-2 pr-4">
                    <span className="text-slate-800 dark:text-slate-200">{row.display}</span>
                    <span className="ml-1 font-mono text-xs text-slate-500 dark:text-slate-500">@{row.username}</span>
                  </td>
                  <td className="py-2 pr-4 font-mono text-xs text-emerald-600/90 dark:text-emerald-400/90">{row.role}</td>
                  <td className="py-2">
                    <button
                      type="button"
                      className="text-xs text-red-600 dark:text-red-400 hover:text-red-700 dark:text-red-300"
                      disabled={revoke.isPending}
                      onClick={() => {
                        if (
                          window.confirm(
                            `Remove ${row.role} from ${row.display} on ${row.projectLabel}?`,
                          )
                        ) {
                          revoke.mutate({
                            userId: row.userId,
                            projectId: row.projectId,
                            role: row.role,
                          });
                        }
                      }}
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
