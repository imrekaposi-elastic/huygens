import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { FlatBreakoutConfig, FlatBreakoutMode } from "@/api/types";
import { Modal } from "@/components/Modal";

const UPLINK_PATTERN = /^[a-zA-Z0-9._-]{1,15}$/;
const OPERATOR_MODES: FlatBreakoutMode[] = ["bridge_uplink", "macvlan"];

type Props = {
  open: boolean;
  projectId: string;
  agentId: string;
  networkName: string;
  onClose: () => void;
  onSaved: () => void;
};

export function FlatBreakoutDialog({
  open,
  projectId,
  agentId,
  networkName,
  onClose,
  onSaved,
}: Props) {
  const [enabled, setEnabled] = useState(false);
  const [mode, setMode] = useState<FlatBreakoutMode>("bridge_uplink");
  const [uplink, setUplink] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const breakout = useQuery({
    queryKey: ["breakout", projectId, agentId, networkName],
    queryFn: () => api.getNetworkBreakout(projectId, agentId, networkName),
    enabled: open && !!networkName,
  });

  const flat = breakout.data?.flat;
  const topologyManaged = Boolean(flat?.enabled && flat.mode === "local_peer");

  useEffect(() => {
    if (!open || !flat) return;
    setErr(null);
    setEnabled(Boolean(flat.enabled));
    if (flat.mode === "local_peer") {
      setMode("bridge_uplink");
      setUplink(flat.uplink ?? "");
    } else {
      setMode(flat.mode);
      setUplink(flat.uplink ?? "");
    }
  }, [open, flat]);

  const save = useMutation({
    mutationFn: async () => {
      if (topologyManaged) {
        throw new ApiError("This network uses topology local_peer breakout.", 400);
      }
      const body: FlatBreakoutConfig = {
        enabled,
        mode,
        uplink: uplink.trim(),
        remote_hypervisor_cidrs: [],
        nat_exempt_cidrs: [],
      };
      if (enabled && !body.uplink) {
        throw new ApiError("Uplink interface is required when flat breakout is enabled.", 400);
      }
      if (body.uplink && !UPLINK_PATTERN.test(body.uplink)) {
        throw new ApiError("Invalid uplink name (1–15 chars: letters, digits, . _ -).", 400);
      }
      return api.putFlatBreakout(projectId, agentId, networkName, body);
    },
    onSuccess: () => {
      onSaved();
      onClose();
    },
    onError: (e: unknown) => {
      setErr(e instanceof ApiError ? e.message : "Save failed");
    },
  });

  const footer = (
    <div className="flex justify-end gap-2">
      <button
        type="button"
        onClick={onClose}
        className="rounded-lg border border-slate-300 dark:border-slate-600 px-4 py-2 text-sm text-slate-800 dark:text-slate-200"
      >
        Cancel
      </button>
      {!topologyManaged && (
        <button
          type="button"
          disabled={save.isPending || breakout.isLoading}
          onClick={() => save.mutate()}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
        >
          {save.isPending ? "Saving…" : "Save"}
        </button>
      )}
    </div>
  );

  return (
    <Modal
      open={open}
      title={`Flat L2 breakout — ${networkName}`}
      onClose={onClose}
      footer={footer}
    >
      {breakout.isLoading && <p className="text-sm text-slate-500">Loading…</p>}
      {breakout.isError && (
        <p className="text-sm text-red-700 dark:text-red-300">Could not load breakout config.</p>
      )}
      {topologyManaged && (
        <p className="mb-3 rounded-lg border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/40 px-3 py-2 text-sm text-amber-900 dark:text-amber-200">
          Managed by a topology <span className="font-mono">local</span> link (
          <span className="font-mono">local_peer</span>). Change or remove the link on the Topology
          page; do not edit flat breakout here.
        </p>
      )}
      {!topologyManaged && breakout.data && (
        <div className="space-y-4 text-sm">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
              className="rounded border-slate-400"
            />
            <span className="text-slate-800 dark:text-slate-200">Enable flat L2 breakout</span>
          </label>
          <div>
            <label className="mb-1 block text-slate-600 dark:text-slate-400">Mode</label>
            <select
              value={mode}
              disabled={!enabled}
              onChange={(e) => setMode(e.target.value as FlatBreakoutMode)}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2"
            >
              {OPERATOR_MODES.map((m) => (
                <option key={m} value={m}>
                  {m === "bridge_uplink" ? "Bridge uplink" : "Macvlan"}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-slate-600 dark:text-slate-400">
              Host uplink interface
            </label>
            <input
              type="text"
              value={uplink}
              disabled={!enabled}
              onChange={(e) => setUplink(e.target.value)}
              placeholder="e.g. eth0"
              className="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 font-mono"
              autoComplete="off"
            />
            <p className="mt-1 text-xs text-slate-500">
              Physical NIC on the hypervisor attached to the libvirt bridge (
              <span className="font-mono">br-&lt;vnet&gt;</span>).
            </p>
          </div>
          {flat?.enabled && flat.mode !== "local_peer" && (
            <p className="text-xs text-slate-500">
              Current agent state:{" "}
              <span className="font-mono">
                {flat.mode}
                {flat.uplink ? ` · ${flat.uplink}` : ""}
              </span>
            </p>
          )}
        </div>
      )}
      {err && <p className="mt-3 text-sm text-red-700 dark:text-red-300">{err}</p>}
    </Modal>
  );
}
