import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthContext";
import type { UserOut } from "@/api/types";
import { api, ApiError } from "@/api/client";
import { ProjectAccessPanel } from "@/components/ProjectAccessPanel";
import { ORG_ROLES } from "@/lib/rbac";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";

function RoleCheckboxes({
  options,
  selected,
  onChange,
}: {
  options: readonly string[];
  selected: string[];
  onChange: (roles: string[]) => void;
}) {
  return (
    <div className="flex flex-wrap gap-3">
      {options.map((role) => (
        <label key={role} className="flex items-center gap-1.5 text-sm">
          <input
            type="checkbox"
            checked={selected.includes(role)}
            onChange={(e) => {
              if (e.target.checked) onChange([...selected, role]);
              else onChange(selected.filter((r) => r !== role));
            }}
          />
          <span className="font-mono text-xs text-slate-700 dark:text-slate-300">{role}</span>
        </label>
      ))}
    </div>
  );
}

export function AdminUsersTab() {
  const { selectedOrgId } = useAuth();
  const qc = useQueryClient();
  const platformAdmin = isPlatformAdmin(getAccessToken());
  const [err, setErr] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [newOrgRoles, setNewOrgRoles] = useState<string[]>(["admin"]);
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [editOrgRoles, setEditOrgRoles] = useState<string[]>([]);
  const { data: users, isLoading } = useQuery({
    queryKey: ["admin", "users", selectedOrgId],
    queryFn: () => api.orgUsers(selectedOrgId!),
    enabled: !!selectedOrgId,
  });

  const createUser = useMutation({
    mutationFn: () =>
      api.createOrgUser(selectedOrgId!, {
        email: email.trim(),
        username: username.trim(),
        password,
        display_name: displayName.trim() || undefined,
        org_roles: newOrgRoles,
      }),
    onSuccess: () => {
      setCreateOpen(false);
      setEmail("");
      setUsername("");
      setPassword("");
      setDisplayName("");
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["admin", "users", selectedOrgId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Create failed"),
  });

  const saveOrgRoles = useMutation({
    mutationFn: ({ userId, roles }: { userId: string; roles: string[] }) =>
      api.updateOrgUserRoles(selectedOrgId!, userId, roles),
    onSuccess: () => {
      setEditingUserId(null);
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["admin", "users", selectedOrgId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Update failed"),
  });

  const grantPlatform = useMutation({
    mutationFn: (userId: string) => api.grantPlatformAdmin(userId),
    onSuccess: () => {
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["admin", "users", selectedOrgId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Grant failed"),
  });

  const removeUser = useMutation({
    mutationFn: (userId: string) => api.deleteOrgUser(selectedOrgId!, userId),
    onSuccess: () => {
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["admin", "users", selectedOrgId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Delete failed"),
  });

  function handleDeleteUser(u: UserOut) {
    const msg =
      u.platform_roles.length > 0
        ? `Remove "${u.username}" from this organization?\n\nThey still have platform roles and may retain global access.`
        : `Delete user "${u.username}" from this organization?\n\nOrg membership and project roles here will be removed. If they belong to no other org, the account is deleted.`;
    if (window.confirm(msg)) removeUser.mutate(u.id);
  }

  if (!selectedOrgId) return <p className="text-slate-600 dark:text-slate-400">Select an organization</p>;

  return (
    <div className="space-y-6">
      <ProjectAccessPanel />

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => setCreateOpen((v) => !v)}
          className="min-h-11 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500"
        >
          {createOpen ? "Cancel" : "Add user"}
        </button>
      </div>

      {createOpen && (
        <form
          className="space-y-4 rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/80 p-4"
          onSubmit={(e) => {
            e.preventDefault();
            createUser.mutate();
          }}
        >
          <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">New organization user</h2>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="text-sm">
              Email
              <input
                type="email"
                required
                className="mt-1 w-full min-h-11 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
            <label className="text-sm">
              Username
              <input
                required
                className="mt-1 w-full min-h-11 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </label>
            <label className="text-sm">
              Password
              <input
                type="password"
                required
                minLength={8}
                className="mt-1 w-full min-h-11 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <label className="text-sm">
              Display name
              <input
                className="mt-1 w-full min-h-11 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            </label>
          </div>
          <div>
            <p className="mb-2 text-sm text-slate-600 dark:text-slate-400">Organization roles</p>
            <RoleCheckboxes options={ORG_ROLES} selected={newOrgRoles} onChange={setNewOrgRoles} />
          </div>
          <button
            type="submit"
            disabled={createUser.isPending}
            className="min-h-11 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            {createUser.isPending ? "Creating…" : "Create user"}
          </button>
        </form>
      )}

      {err && <p className="text-sm text-red-600 dark:text-red-400">{err}</p>}
      {isLoading && <p className="text-slate-600 dark:text-slate-400">Loading users…</p>}

      <ul className="space-y-3">
        {users?.map((u) => {
          const orgMembership = u.org_memberships.find((m) => m.organization_id === selectedOrgId);
          const orgRoles = orgMembership?.roles ?? [];
          const editing = editingUserId === u.id;

          return (
            <li key={u.id} className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/80 p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-medium">
                    {u.display_name || u.username}
                    <span className="ml-2 font-normal text-sm text-slate-500 dark:text-slate-500">{u.email}</span>
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-500 font-mono">
                    @{u.username}
                    {!u.is_active && (
                      <span className="ml-2 text-amber-700 dark:text-amber-400">inactive</span>
                    )}
                  </p>
                  {u.platform_roles.length > 0 && (
                    <p className="mt-1 text-xs text-emerald-600/90 dark:text-emerald-400/90">
                      Platform: {u.platform_roles.join(", ")}
                    </p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {!editing && (
                    <button
                      type="button"
                      className="min-h-9 rounded border border-slate-300 dark:border-slate-600 px-3 text-sm hover:bg-slate-50 dark:bg-slate-800"
                      onClick={() => {
                        setEditingUserId(u.id);
                        setEditOrgRoles([...orgRoles]);
                      }}
                    >
                      Edit org roles
                    </button>
                  )}
                  {platformAdmin && !u.platform_roles.includes("platform_admin") && (
                    <button
                      type="button"
                      className="min-h-9 rounded border border-emerald-800 px-3 text-sm text-emerald-700 dark:text-emerald-300 hover:bg-emerald-950/40"
                      disabled={grantPlatform.isPending}
                      onClick={() => {
                        if (
                          window.confirm(
                            `Grant platform_admin to ${u.username}? This is full platform access.`,
                          )
                        ) {
                          grantPlatform.mutate(u.id);
                        }
                      }}
                    >
                      Grant platform admin
                    </button>
                  )}
                  <button
                    type="button"
                    className="min-h-9 rounded border border-red-300 dark:border-red-900/80 px-3 text-sm text-red-700 dark:text-red-300 hover:bg-red-50 dark:bg-red-950/40"
                    disabled={removeUser.isPending}
                    onClick={() => handleDeleteUser(u)}
                  >
                    Delete user
                  </button>
                </div>
              </div>

              {editing ? (
                <div className="mt-3 space-y-2">
                  <RoleCheckboxes
                    options={ORG_ROLES}
                    selected={editOrgRoles}
                    onChange={setEditOrgRoles}
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="min-h-9 rounded bg-emerald-600 px-3 text-sm hover:bg-emerald-500"
                      disabled={saveOrgRoles.isPending}
                      onClick={() => saveOrgRoles.mutate({ userId: u.id, roles: editOrgRoles })}
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      className="min-h-9 rounded border border-slate-300 dark:border-slate-600 px-3 text-sm"
                      onClick={() => setEditingUserId(null)}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                  Org roles:{" "}
                  <span className="font-mono text-slate-700 dark:text-slate-300">
                    {orgRoles.length ? orgRoles.join(", ") : "—"}
                  </span>
                </p>
              )}

            </li>
          );
        })}
      </ul>
    </div>
  );
}
