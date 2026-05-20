import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import { Modal } from "@/components/Modal";

type VmRecord = Record<string, unknown>;

type Props = {
  open: boolean;
  mode: "create" | "edit";
  projectId: string;
  agentId: string;
  initial?: VmRecord | null;
  onClose: () => void;
  onSaved: () => void;
};

export function VmDialog({ open, mode, projectId, agentId, initial, onClose, onSaved }: Props) {
  const [name, setName] = useState("");
  const [imageName, setImageName] = useState("");
  const [cloudInitProfile, setCloudInitProfile] = useState("");
  const [network, setNetwork] = useState("default");
  const [vcpu, setVcpu] = useState("2");
  const [memoryMib, setMemoryMib] = useState("2048");
  const [autostart, setAutostart] = useState(false);
  const [start, setStart] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const profiles = useQuery({
    queryKey: ["cloud-init", projectId, agentId],
    queryFn: () => api.listCloudInitProfiles(projectId, agentId),
    enabled: open && !!agentId,
  });

  const profileNames =
    profiles.data?.map((p) => String(p.name ?? "")).filter(Boolean) ?? [];

  useEffect(() => {
    if (!open) return;
    setErr(null);
    if (mode === "edit" && initial) {
      setName(String(initial.name ?? ""));
      setNetwork(String(initial.network ?? "default"));
      setVcpu(String(initial.vcpu ?? 2));
      setMemoryMib(String(initial.memory_mib ?? 2048));
      setAutostart(Boolean(initial.autostart));
    } else {
      setName("");
      setImageName("");
      setCloudInitProfile("");
      setNetwork("default");
      setVcpu("2");
      setMemoryMib("2048");
      setAutostart(false);
      setStart(true);
    }
  }, [open, mode, initial]);

  const save = useMutation({
    mutationFn: async (confirmReboot: boolean) => {
      if (mode === "create") {
        return api.createVm(projectId, agentId, {
          name: name.trim(),
          image_name: imageName.trim(),
          cloud_init_profile: cloudInitProfile.trim(),
          network: network.trim() || "default",
          vcpu: parseInt(vcpu, 10) || 2,
          memory_mib: parseInt(memoryMib, 10) || 2048,
          start,
        });
      }
      return api.patchVm(projectId, agentId, name, {
        vcpu: parseInt(vcpu, 10) || undefined,
        memory_mib: parseInt(memoryMib, 10) || undefined,
        autostart,
        confirm_reboot: confirmReboot,
      });
    },
    onSuccess: () => {
      onSaved();
      onClose();
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Save failed"),
  });

  const handleSave = () => {
    if (mode === "edit" && initial) {
      const vcpuChanged = parseInt(vcpu, 10) !== Number(initial.vcpu);
      const memChanged = parseInt(memoryMib, 10) !== Number(initial.memory_mib);
      const hardwareChanged = vcpuChanged || memChanged;
      const isRunning = String(initial.libvirt_state ?? "").toUpperCase() === "RUNNING";
      if (hardwareChanged && isRunning) {
        const ok = window.confirm(
          `Changing memory or vCPUs on "${name}" requires stopping and starting the VM on the hypervisor.\n\nProceed with reboot?`,
        );
        if (!ok) return;
        save.mutate(true);
        return;
      }
      save.mutate(false);
      return;
    }
    save.mutate(false);
  };

  return (
    <Modal
      open={open}
      title={mode === "create" ? "New virtual machine" : `Edit ${name}`}
      onClose={onClose}
      footer={
        <>
          <button type="button" onClick={onClose} className="min-h-10 rounded-lg border border-slate-600 px-4 text-sm">
            Cancel
          </button>
          <button
            type="button"
            disabled={save.isPending}
            onClick={handleSave}
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
              Image name
              <input
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-700 bg-slate-800 px-3 font-mono text-sm"
                value={imageName}
                onChange={(e) => setImageName(e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              Cloud-init profile
              <select
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-700 bg-slate-800 px-3"
                value={cloudInitProfile}
                onChange={(e) => setCloudInitProfile(e.target.value)}
                required
              >
                <option value="">Select profile…</option>
                {profileNames.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Network
              <input
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-700 bg-slate-800 px-3"
                value={network}
                onChange={(e) => setNetwork(e.target.value)}
              />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block text-sm">
                vCPU
                <input
                  type="number"
                  min={1}
                  className="mt-1 w-full min-h-10 rounded-lg border border-slate-700 bg-slate-800 px-3"
                  value={vcpu}
                  onChange={(e) => setVcpu(e.target.value)}
                />
              </label>
              <label className="block text-sm">
                Memory (MB)
                <input
                  type="number"
                  min={256}
                  className="mt-1 w-full min-h-10 rounded-lg border border-slate-700 bg-slate-800 px-3"
                  value={memoryMib}
                  onChange={(e) => setMemoryMib(e.target.value)}
                />
              </label>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={start} onChange={(e) => setStart(e.target.checked)} />
              Start after create
            </label>
          </>
        ) : (
          <>
            <p className="text-xs text-slate-500">
              Power: {String(initial?.libvirt_state ?? "unknown")}. Hardware changes on a running VM
              need your confirmation before the agent reboots the guest.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <label className="block text-sm">
                vCPU
                <input
                  type="number"
                  min={1}
                  className="mt-1 w-full min-h-10 rounded-lg border border-slate-700 bg-slate-800 px-3"
                  value={vcpu}
                  onChange={(e) => setVcpu(e.target.value)}
                />
              </label>
              <label className="block text-sm">
                Memory (MB)
                <input
                  type="number"
                  min={256}
                  className="mt-1 w-full min-h-10 rounded-lg border border-slate-700 bg-slate-800 px-3"
                  value={memoryMib}
                  onChange={(e) => setMemoryMib(e.target.value)}
                />
              </label>
            </div>
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
