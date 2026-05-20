import { useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthContext";
import { api, ApiError } from "@/api/client";
import type { IdpGroupMapping } from "@/api/types";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";

function MappingForm({
  initial,
  onSubmit,
  onCancel,
  busy,
}: {
  initial?: Partial<IdpGroupMapping>;
  onSubmit: (body: {
    idp_group_name: string;
    match_type: string;
    huy_role: string;
    priority: number;
    enabled: boolean;
  }) => void;
  onCancel: () => void;
  busy: boolean;
}) {
  const [idpGroup, setIdpGroup] = useState(initial?.idp_group_name ?? "");
  const [matchType, setMatchType] = useState(initial?.match_type ?? "exact");
  const [huyRole, setHuyRole] = useState(initial?.huy_role ?? "");
  const [priority, setPriority] = useState(String(initial?.priority ?? 0));
  const [enabled, setEnabled] = useState(initial?.enabled ?? true);

  return (
    <form
      className="mt-3 grid gap-3 rounded border border-slate-300 dark:border-slate-700 bg-red-50/90 dark:bg-red-950/50 p-3 md:grid-cols-2"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({
          idp_group_name: idpGroup.trim(),
          match_type: matchType,
          huy_role: huyRole.trim(),
          priority: Number(priority) || 0,
          enabled,
        });
      }}
    >
      <label className="text-sm md:col-span-2">
        IdP group name
        <input
          required
          className="mt-1 w-full min-h-11 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
          value={idpGroup}
          onChange={(e) => setIdpGroup(e.target.value)}
          placeholder="e.g. huygens-admins"
        />
      </label>
      <label className="text-sm">
        Match
        <select
          className="mt-1 w-full min-h-11 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-2"
          value={matchType}
          onChange={(e) => setMatchType(e.target.value)}
        >
          <option value="exact">exact</option>
          <option value="regex">regex</option>
        </select>
      </label>
      <label className="text-sm">
        Huygens role
        <input
          required
          className="mt-1 w-full min-h-11 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
          value={huyRole}
          onChange={(e) => setHuyRole(e.target.value)}
          placeholder="admin, platform_admin, project_admin, …"
        />
      </label>
      <label className="text-sm">
        Priority
        <input
          type="number"
          className="mt-1 w-full min-h-11 rounded border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
        />
      </label>
      <label className="flex items-center gap-2 text-sm md:col-span-2">
        <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
        Enabled
      </label>
      <div className="flex gap-2 md:col-span-2">
        <button
          type="submit"
          disabled={busy}
          className="min-h-11 rounded bg-emerald-600 px-4 text-sm hover:bg-emerald-500 disabled:opacity-50"
        >
          Save
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="min-h-11 rounded border border-slate-300 dark:border-slate-600 px-4 text-sm"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

function MappingTable({
  title,
  mappings,
  editingId,
  setEditingId,
  onDelete,
  onPatch,
  createSlot,
}: {
  title: string;
  mappings: IdpGroupMapping[];
  editingId: string | null;
  setEditingId: (id: string | null) => void;
  onDelete: (id: string) => void;
  onPatch: (
    id: string,
    body: {
      idp_group_name: string;
      match_type: string;
      huy_role: string;
      priority: number;
      enabled: boolean;
    },
  ) => void;
  createSlot?: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/80 p-4">
      <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">{title}</h2>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">
        Maps IdP (Keycloak) group membership to Huygens roles at login. Higher priority wins.
      </p>
      {createSlot}
      {mappings.length === 0 && !createSlot && (
        <p className="mt-3 text-sm text-slate-500 dark:text-slate-500">No mappings configured.</p>
      )}
      <ul className="mt-3 space-y-2">
        {mappings.map((m) => (
          <li key={m.id} className="rounded border border-slate-200 dark:border-slate-800 bg-red-50 dark:bg-red-950/40 p-3">
            {editingId === m.id ? (
              <MappingForm
                initial={m}
                busy={false}
                onCancel={() => setEditingId(null)}
                onSubmit={(body) => onPatch(m.id, body)}
              />
            ) : (
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="font-mono text-sm">
                  <span className="text-slate-800 dark:text-slate-200">{m.idp_group_name}</span>
                  <span className="mx-2 text-slate-600">→</span>
                  <span className="text-emerald-600 dark:text-emerald-400">{m.huy_role}</span>
                  <span className="ml-2 text-xs text-slate-500 dark:text-slate-500">
                    ({m.match_type}, priority {m.priority}
                    {!m.enabled && ", disabled"})
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-900 dark:text-white"
                    onClick={() => setEditingId(m.id)}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:text-red-300"
                    onClick={() => {
                      if (window.confirm(`Delete mapping for "${m.idp_group_name}"?`)) {
                        onDelete(m.id);
                      }
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function AdminIdpMappingsTab() {
  const { selectedOrgId } = useAuth();
  const qc = useQueryClient();
  const platformAdmin = isPlatformAdmin(getAccessToken());
  const [err, setErr] = useState<string | null>(null);
  const [orgCreateOpen, setOrgCreateOpen] = useState(false);
  const [platformCreateOpen, setPlatformCreateOpen] = useState(false);
  const [editingOrgId, setEditingOrgId] = useState<string | null>(null);
  const [editingPlatformId, setEditingPlatformId] = useState<string | null>(null);

  const orgMappings = useQuery({
    queryKey: ["admin", "idp", "org", selectedOrgId],
    queryFn: () => api.orgIdpMappings(selectedOrgId!),
    enabled: !!selectedOrgId,
  });

  const platformMappings = useQuery({
    queryKey: ["admin", "idp", "platform"],
    queryFn: () => api.platformIdpMappings(),
    enabled: platformAdmin,
  });

  const invalidateOrg = () =>
    void qc.invalidateQueries({ queryKey: ["admin", "idp", "org", selectedOrgId] });
  const invalidatePlatform = () =>
    void qc.invalidateQueries({ queryKey: ["admin", "idp", "platform"] });

  if (!selectedOrgId) return <p className="text-slate-600 dark:text-slate-400">Select an organization</p>;

  return (
    <div className="space-y-6">
      {err && <p className="text-sm text-red-600 dark:text-red-400">{err}</p>}

      <MappingTable
        title="Organization IdP group mappings"
        mappings={orgMappings.data ?? []}
        editingId={editingOrgId}
        setEditingId={setEditingOrgId}
        onDelete={(id) => {
          api
            .deleteOrgIdpMapping(selectedOrgId, id)
            .then(invalidateOrg)
            .catch((e) => setErr(e instanceof ApiError ? e.message : "Delete failed"));
        }}
        onPatch={(id, body) => {
          api
            .patchOrgIdpMapping(selectedOrgId, id, body)
            .then(() => {
              setEditingOrgId(null);
              invalidateOrg();
            })
            .catch((e) => setErr(e instanceof ApiError ? e.message : "Update failed"));
        }}
        createSlot={
          <>
            {!orgCreateOpen ? (
              <button
                type="button"
                className="mt-3 min-h-11 rounded-lg border border-slate-300 dark:border-slate-600 px-4 text-sm hover:bg-slate-50 dark:bg-slate-800"
                onClick={() => setOrgCreateOpen(true)}
              >
                Add org mapping
              </button>
            ) : (
              <MappingForm
                busy={false}
                onCancel={() => setOrgCreateOpen(false)}
                onSubmit={(body) => {
                  api
                    .createOrgIdpMapping(selectedOrgId, body)
                    .then(() => {
                      setOrgCreateOpen(false);
                      invalidateOrg();
                    })
                    .catch((e) =>
                      setErr(e instanceof ApiError ? e.message : "Create failed"),
                    );
                }}
              />
            )}
          </>
        }
      />

      {platformAdmin && (
        <MappingTable
          title="Platform IdP group mappings"
          mappings={platformMappings.data ?? []}
          editingId={editingPlatformId}
          setEditingId={setEditingPlatformId}
          onDelete={(id) => {
            api
              .deletePlatformIdpMapping(id)
              .then(invalidatePlatform)
              .catch((e) => setErr(e instanceof ApiError ? e.message : "Delete failed"));
          }}
          onPatch={(id, body) => {
            api
              .patchPlatformIdpMapping(id, body)
              .then(() => {
                setEditingPlatformId(null);
                invalidatePlatform();
              })
              .catch((e) => setErr(e instanceof ApiError ? e.message : "Update failed"));
          }}
          createSlot={
            <>
              {!platformCreateOpen ? (
                <button
                  type="button"
                  className="mt-3 min-h-11 rounded-lg border border-slate-300 dark:border-slate-600 px-4 text-sm hover:bg-slate-50 dark:bg-slate-800"
                  onClick={() => setPlatformCreateOpen(true)}
                >
                  Add platform mapping
                </button>
              ) : (
                <MappingForm
                  busy={false}
                  onCancel={() => setPlatformCreateOpen(false)}
                  onSubmit={(body) => {
                    api
                      .createPlatformIdpMapping(body)
                      .then(() => {
                        setPlatformCreateOpen(false);
                        invalidatePlatform();
                      })
                      .catch((e) =>
                        setErr(e instanceof ApiError ? e.message : "Create failed"),
                      );
                  }}
                />
              )}
            </>
          }
        />
      )}
    </div>
  );
}
