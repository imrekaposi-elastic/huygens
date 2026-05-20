import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import { Modal } from "@/components/Modal";

type NetRecord = Record<string, unknown>;

type Props = {
  open: boolean;
  mode: "create" | "edit";
  projectId: string;
  organizationId: string;
  agentId: string;
  initial?: NetRecord | null;
  onClose: () => void;
  onSaved: () => void;
};

export function NetworkDialog({
  open,
  mode,
  projectId,
  organizationId,
  agentId,
  initial,
  onClose,
  onSaved,
}: Props) {
  const [name, setName] = useState("");
  const [allocationId, setAllocationId] = useState("");
  const [ipv4Cidr, setIpv4Cidr] = useState("");
  const [autostart, setAutostart] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const allocations = useQuery({
    queryKey: ["ipam-allocations", organizationId, projectId],
    queryFn: () => api.listProjectIpAllocations(organizationId, projectId),
    enabled: open && mode === "create" && !!organizationId,
  });

  const available = useMemo(
    () => (allocations.data ?? []).filter((a) => a.status === "reserved"),
    [allocations.data],
  );

  useEffect(() => {
    if (!open) return;
    setErr(null);
    if (mode === "edit" && initial) {
      setName(String(initial.name ?? ""));
      setAutostart(Boolean(initial.autostart ?? true));
      setIpv4Cidr(String(initial.ipv4_cidr ?? ""));
    } else {
      setName("");
      setIpv4Cidr("");
      setAutostart(true);
    }
  }, [open, mode, initial]);

  useEffect(() => {
    if (!open || mode !== "create") return;
    if (available.length && !allocationId) {
      setAllocationId(available[0].id);
    }
  }, [open, mode, available, allocationId]);

  const selectedAllocation = available.find((a) => a.id === allocationId);

  const save = useMutation({
    mutationFn: async () => {
      if (mode === "create") {
        if (!allocationId) {
          throw new ApiError("Select a subnet block from General first.", 400);
        }
        return api.createNetwork(projectId, agentId, {
          name: name.trim(),
          allocation_id: allocationId,
        });
      }
      return api.patchNetwork(projectId, agentId, name, {
        autostart,
        ipv4_cidr: ipv4Cidr.trim() || undefined,
      });
    },
    onSuccess: () => {
      onSaved();
      onClose();
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Save failed"),
  });

  return (
    <Modal
      open={open}
      title={mode === "create" ? "New virtual network" : `Edit ${name}`}
      onClose={onClose}
      footer={
        <>
          <button type="button" onClick={onClose} className="min-h-10 rounded-lg border border-slate-300 dark:border-slate-600 px-4 text-sm">
            Cancel
          </button>
          <button
            type="button"
            disabled={save.isPending || (mode === "create" && (available.length === 0 || !name.trim()))}
            onClick={() => save.mutate()}
            className="min-h-10 rounded-lg bg-emerald-600 px-5 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            {save.isPending ? "Saving…" : "Save"}
          </button>
        </>
      }
    >
      <div className="space-y-3">
        {err && <p className="text-sm text-red-700 dark:text-red-300">{err}</p>}
        {mode === "create" ? (
          <>
            {allocations.isLoading && (
              <p className="text-xs text-slate-500 dark:text-slate-500">Loading subnet blocks…</p>
            )}
            {available.length === 0 && !allocations.isLoading && (
              <p className="rounded-lg bg-amber-50 dark:bg-amber-950/40 px-3 py-2 text-sm text-amber-900 dark:text-amber-200">
                No subnet blocks are assigned to this project. An organization admin must assign blocks in{" "}
                <strong>IPAM</strong> (sidebar), then you can create networks here.
              </p>
            )}
            {available.length > 0 && (
              <label className="block text-sm">
                Subnet block
                <select
                  className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
                  value={allocationId}
                  onChange={(e) => setAllocationId(e.target.value)}
                >
                  {available.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.cidr}
                    </option>
                  ))}
                </select>
                <span className="mt-1 block text-xs text-slate-500 dark:text-slate-500">
                  CIDR comes from your organization pool — no manual addressing needed.
                </span>
              </label>
            )}
            <label className="block text-sm">
              Network name
              <input
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={selectedAllocation ? "lab0" : "lab0"}
                required
              />
              <span className="mt-1 block text-xs text-slate-500 dark:text-slate-500">
                Short name used when attaching VMs (e.g. lab0, app-net).
              </span>
            </label>
          </>
        ) : (
          <>
            <label className="block text-sm">
              IPv4 CIDR
              <input
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
                value={ipv4Cidr}
                onChange={(e) => setIpv4Cidr(e.target.value)}
              />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={autostart}
                onChange={(e) => setAutostart(e.target.checked)}
              />
              Autostart
            </label>
          </>
        )}
      </div>
    </Modal>
  );
}
