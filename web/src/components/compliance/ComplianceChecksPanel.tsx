import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/auth/AuthContext";
import { api, ApiError } from "@/api/client";
import type { ComplianceCheck, UserOut } from "@/api/types";

type Props = {
  organizationId: string;
  canManage: boolean;
  catalogItemOptions: { id: string; name: string }[];
  onError: (msg: string) => void;
  /** When true, list and forms are visible immediately (dedicated Checks page). */
  defaultOpen?: boolean;
};

function ownerLabel(user: UserOut) {
  const name = user.display_name?.trim() || user.username;
  return `${name} (${user.email})`;
}

function resolveOwnerDisplay(userId: string, users: UserOut[]) {
  const u = users.find((x) => x.id === userId);
  if (!u) return null;
  return u.display_name?.trim() || u.username;
}

function CheckRow({
  check,
  canManage,
  organizationId,
  catalogItemOptions,
  orgUsers,
  onError,
}: {
  check: ComplianceCheck;
  canManage: boolean;
  organizationId: string;
  catalogItemOptions: { id: string; name: string }[];
  orgUsers: UserOut[];
  onError: (msg: string) => void;
}) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [ownerUserId, setOwnerUserId] = useState(check.owner_user_id);
  const [validUntil, setValidUntil] = useState(check.valid_until.slice(0, 10));
  const [status, setStatus] = useState(check.status);

  const ownerName =
    orgUsers.find((u) => u.id === check.owner_user_id)?.display_name ||
    orgUsers.find((u) => u.id === check.owner_user_id)?.username ||
    check.owner_display ||
    check.owner_user_id;

  const save = useMutation({
    mutationFn: () =>
      api.updateComplianceCheck(organizationId, check.id, {
        owner_user_id: ownerUserId,
        owner_display: resolveOwnerDisplay(ownerUserId, orgUsers) ?? undefined,
        valid_until: new Date(validUntil).toISOString(),
        status: status as "active" | "expired" | "waived",
      }),
    onSuccess: () => {
      setEditing(false);
      void qc.invalidateQueries({ queryKey: ["compliance-checks", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-dashboard", organizationId] });
    },
    onError: (e) => onError(e instanceof ApiError ? e.message : "Update failed"),
  });

  const remove = useMutation({
    mutationFn: () => api.deleteComplianceCheck(organizationId, check.id),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["compliance-checks", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-dashboard", organizationId] });
    },
    onError: (e) => onError(e instanceof ApiError ? e.message : "Delete failed"),
  });

  if (editing && canManage) {
    return (
      <li className="space-y-2 rounded-lg border border-emerald-500/40 bg-emerald-50/50 p-3 dark:bg-emerald-950/20">
        <p className="text-sm font-medium">
          {check.compliance_item_name ??
            catalogItemOptions.find((c) => c.id === check.compliance_item_id)?.name}
        </p>
        <label className="block text-sm">
          Owner (org user)
          <select
            className="mt-1 w-full min-h-9 rounded border border-slate-300 px-2 dark:border-slate-700 dark:bg-slate-800"
            value={ownerUserId}
            onChange={(e) => setOwnerUserId(e.target.value)}
          >
            {orgUsers.map((u) => (
              <option key={u.id} value={u.id}>
                {ownerLabel(u)}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          Valid until
          <input
            type="date"
            className="mt-1 w-full min-h-9 rounded border border-slate-300 px-2 dark:border-slate-700 dark:bg-slate-800"
            value={validUntil}
            onChange={(e) => setValidUntil(e.target.value)}
          />
        </label>
        <label className="block text-sm">
          Status
          <select
            className="mt-1 w-full min-h-9 rounded border border-slate-300 px-2 dark:border-slate-700 dark:bg-slate-800"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="active">active</option>
            <option value="expired">expired</option>
            <option value="waived">waived</option>
          </select>
        </label>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={save.isPending}
            onClick={() => save.mutate()}
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
        <span className="font-medium">{check.compliance_item_name ?? check.compliance_item_id}</span>
        <span className="mx-2 text-slate-400">·</span>
        {ownerName}
        <span className="mx-2 text-slate-400">·</span>
        valid until {new Date(check.valid_until).toLocaleDateString()}
        <span className="mx-2 text-xs uppercase text-slate-500">{check.status}</span>
        {check.days_until_expiry != null && check.days_until_expiry <= 30 && check.status === "active" && (
          <span className="ml-2 rounded bg-amber-100 px-1.5 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
            {check.days_until_expiry}d left
          </span>
        )}
      </span>
      {canManage && (
        <span className="flex gap-2">
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
            disabled={remove.isPending}
            onClick={() => {
              const label = check.compliance_item_name ?? check.compliance_item_id;
              if (window.confirm(`Delete compliance check for "${label}"?`)) {
                remove.mutate();
              }
            }}
          >
            Delete
          </button>
        </span>
      )}
    </li>
  );
}

export function ComplianceChecksPanel({
  organizationId,
  canManage,
  catalogItemOptions,
  onError,
  defaultOpen = false,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const { user } = useAuth();
  const qc = useQueryClient();
  const [checkItemId, setCheckItemId] = useState("");
  const [checkOwnerUserId, setCheckOwnerUserId] = useState("");
  const [checkValidUntil, setCheckValidUntil] = useState("");

  const checks = useQuery({
    queryKey: ["compliance-checks", organizationId],
    queryFn: () => api.listComplianceChecks(organizationId),
  });

  const orgUsers = useQuery({
    queryKey: ["org-users", organizationId],
    queryFn: () => api.orgUsers(organizationId),
    enabled: open && !!organizationId,
  });

  const users = orgUsers.data ?? [];
  const checkCount = checks.data?.length ?? 0;

  useEffect(() => {
    if (open && user?.id && users.some((u) => u.id === user.id) && !checkOwnerUserId) {
      setCheckOwnerUserId(user.id);
    }
  }, [open, user?.id, users, checkOwnerUserId]);

  const createCheck = useMutation({
    mutationFn: () => {
      if (!checkItemId || !checkOwnerUserId || !checkValidUntil) {
        throw new Error("Select catalog item, owner, and validity date");
      }
      const owner = users.find((u) => u.id === checkOwnerUserId);
      if (!owner) throw new Error("Select an organization user as owner");
      return api.createComplianceCheck(organizationId, {
        compliance_item_id: checkItemId,
        owner_user_id: owner.id,
        owner_display: owner.display_name?.trim() || owner.username,
        valid_until: new Date(checkValidUntil).toISOString(),
      });
    },
    onSuccess: () => {
      setCheckItemId("");
      setCheckValidUntil("");
      void qc.invalidateQueries({ queryKey: ["compliance-checks", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-dashboard", organizationId] });
    },
    onError: (e) => onError(e instanceof ApiError ? e.message : "Check create failed"),
  });

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-2 text-left"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">
          Compliance checks
          <span className="ml-2 font-normal text-slate-500">({checkCount})</span>
        </h2>
        <span className="text-slate-400" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
      </button>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        Validity-tracked attestations; owner is an organization user account.
      </p>

      {open && (
        <div className="mt-4">
          {orgUsers.isLoading && <p className="text-sm text-slate-500">Loading users…</p>}
          {orgUsers.isError && (
            <p className="text-sm text-amber-700 dark:text-amber-300">
              Could not load org users for owner picker. Create users under Admin.
            </p>
          )}
          <ul className="mb-4 divide-y divide-slate-100 dark:divide-slate-800">
            {(checks.data ?? []).map((c) => (
              <CheckRow
                key={c.id}
                check={c}
                canManage={canManage}
                organizationId={organizationId}
                catalogItemOptions={catalogItemOptions}
                orgUsers={users}
                onError={onError}
              />
            ))}
            {!checks.data?.length && (
              <li className="py-4 text-center text-sm text-slate-500">No checks yet.</li>
            )}
          </ul>
          {canManage && (
            <form
              className="grid gap-3 md:grid-cols-2 lg:grid-cols-4"
              onSubmit={(e) => {
                e.preventDefault();
                createCheck.mutate();
              }}
            >
              <label className="text-sm md:col-span-2">
                Catalog item
                <select
                  className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 dark:border-slate-700 dark:bg-slate-800"
                  value={checkItemId}
                  onChange={(e) => setCheckItemId(e.target.value)}
                  required
                >
                  <option value="">— Select —</option>
                  {catalogItemOptions.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                Owner (org user)
                <select
                  className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 dark:border-slate-700 dark:bg-slate-800"
                  value={checkOwnerUserId}
                  onChange={(e) => setCheckOwnerUserId(e.target.value)}
                  required
                  disabled={!users.length}
                >
                  <option value="">— Select user —</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>
                      {ownerLabel(u)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm">
                Valid until
                <input
                  type="date"
                  className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 dark:border-slate-700 dark:bg-slate-800"
                  value={checkValidUntil}
                  onChange={(e) => setCheckValidUntil(e.target.value)}
                  required
                />
              </label>
              <button
                type="submit"
                disabled={createCheck.isPending || !users.length}
                className="min-h-10 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50 md:col-span-4 lg:col-span-1"
              >
                Add check
              </button>
            </form>
          )}
        </div>
      )}
    </section>
  );
}
