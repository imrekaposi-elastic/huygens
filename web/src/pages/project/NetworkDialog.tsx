import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import { Modal } from "@/components/Modal";

type NetRecord = Record<string, unknown>;

type Props = {
  open: boolean;
  mode: "create" | "edit";
  projectId: string;
  agentId: string;
  initial?: NetRecord | null;
  onClose: () => void;
  onSaved: () => void;
};

export function NetworkDialog({
  open,
  mode,
  projectId,
  agentId,
  initial,
  onClose,
  onSaved,
}: Props) {
  const [name, setName] = useState("");
  const [ipamHosts, setIpamHosts] = useState("10");
  const [ipv4Cidr, setIpv4Cidr] = useState("");
  const [autostart, setAutostart] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setErr(null);
    if (mode === "edit" && initial) {
      setName(String(initial.name ?? ""));
      setAutostart(Boolean(initial.autostart ?? true));
      setIpv4Cidr(String(initial.ipv4_cidr ?? ""));
    } else {
      setName("");
      setIpamHosts("10");
      setIpv4Cidr("");
      setAutostart(true);
    }
  }, [open, mode, initial]);

  const save = useMutation({
    mutationFn: async () => {
      if (mode === "create") {
        const body: Record<string, unknown> = { name: name.trim() };
        if (ipv4Cidr.trim()) {
          body.ipv4_cidr = ipv4Cidr.trim();
        } else {
          body.ipam = { hosts: parseInt(ipamHosts, 10) || 10 };
        }
        return api.createNetwork(projectId, agentId, body);
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
          <button type="button" onClick={onClose} className="min-h-10 rounded-lg border border-slate-600 px-4 text-sm">
            Cancel
          </button>
          <button
            type="button"
            disabled={save.isPending}
            onClick={() => save.mutate()}
            className="min-h-10 rounded-lg bg-emerald-600 px-5 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            {save.isPending ? "Saving…" : "Save"}
          </button>
        </>
      }
    >
      <div className="space-y-3">
        {err && <p className="text-sm text-red-300">{err}</p>}
        {mode === "create" ? (
          <>
            <label className="block text-sm">
              Name
              <input
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-700 bg-slate-800 px-3"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              IPAM hosts (subnet size)
              <input
                type="number"
                min={4}
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-700 bg-slate-800 px-3"
                value={ipamHosts}
                onChange={(e) => setIpamHosts(e.target.value)}
              />
              <span className="mt-1 block text-xs text-slate-500">
                Or set manual CIDR below (org IPAM rules apply).
              </span>
            </label>
            <label className="block text-sm">
              IPv4 CIDR (optional)
              <input
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-700 bg-slate-800 px-3 font-mono text-sm"
                placeholder="192.168.50.0/24"
                value={ipv4Cidr}
                onChange={(e) => setIpv4Cidr(e.target.value)}
              />
            </label>
          </>
        ) : (
          <>
            <label className="block text-sm">
              IPv4 CIDR
              <input
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-700 bg-slate-800 px-3 font-mono text-sm"
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
