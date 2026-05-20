import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import { Modal } from "@/components/Modal";
import { networksForVmSelect } from "@/lib/systemNetwork";

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
  const [network, setNetwork] = useState("");
  const [vcpu, setVcpu] = useState("2");
  const [memoryMib, setMemoryMib] = useState("2048");
  const [autostart, setAutostart] = useState(false);
  const [start, setStart] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const profiles = useQuery({
    queryKey: ["cloud-init", projectId, agentId],
    queryFn: () => api.listCloudInitProfiles(projectId, agentId),
    enabled: open && !!agentId && mode === "create",
  });

  const images = useQuery({
    queryKey: ["images", projectId, agentId],
    queryFn: () => api.listImages(projectId, agentId),
    enabled: open && !!agentId && mode === "create",
  });

  const networks = useQuery({
    queryKey: ["networks", projectId, agentId],
    queryFn: () => api.listNetworks(projectId, agentId),
    enabled: open && !!agentId && mode === "create",
  });

  const readyImages = useMemo(
    () =>
      (images.data ?? [])
        .map((row) => row as Record<string, unknown>)
        .filter((row) => String(row.status ?? "") === "ready" && row.name)
        .map((row) => String(row.name)),
    [images.data],
  );

  const profileNames = useMemo(
    () =>
      (profiles.data ?? [])
        .map((p) => String((p as Record<string, unknown>).name ?? ""))
        .filter(Boolean),
    [profiles.data],
  );

  const networkNames = useMemo(
    () =>
      networksForVmSelect(
        (networks.data ?? []) as { name: string | null; readonly?: boolean }[],
      )
        .map((n) => String(n.name))
        .filter(Boolean),
    [networks.data],
  );

  useEffect(() => {
    if (!open) return;
    setErr(null);
    if (mode === "edit" && initial) {
      setName(String(initial.name ?? ""));
      setVcpu(String(initial.vcpu ?? 2));
      setMemoryMib(String(initial.memory_mib ?? 2048));
      setAutostart(Boolean(initial.autostart));
    } else {
      setName("");
      setImageName("");
      setCloudInitProfile("");
      setNetwork("");
      setVcpu("2");
      setMemoryMib("2048");
      setAutostart(false);
      setStart(true);
    }
  }, [open, mode, initial]);

  useEffect(() => {
    if (!open || mode !== "create") return;
    if (!imageName && readyImages.length > 0) setImageName(readyImages[0]);
    if (!cloudInitProfile && profileNames.length > 0) setCloudInitProfile(profileNames[0]);
    if (!network && networkNames.length > 0) setNetwork(networkNames[0]);
  }, [open, mode, readyImages, profileNames, networkNames, imageName, cloudInitProfile, network]);

  const save = useMutation({
    mutationFn: async (confirmReboot: boolean) => {
      if (mode === "create") {
        return api.createVm(projectId, agentId, {
          name: name.trim(),
          image_name: imageName,
          cloud_init_profile: cloudInitProfile,
          network,
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

  const createReady =
    mode === "create" &&
    name.trim() &&
    imageName &&
    cloudInitProfile &&
    network &&
    readyImages.length > 0 &&
    profileNames.length > 0 &&
    networkNames.length > 0;

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
          <button type="button" onClick={onClose} className="min-h-10 rounded-lg border border-slate-300 dark:border-slate-600 px-4 text-sm">
            Cancel
          </button>
          <button
            type="button"
            disabled={save.isPending || (mode === "create" && !createReady)}
            onClick={handleSave}
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
            {(images.isLoading || profiles.isLoading || networks.isLoading) && (
              <p className="text-xs text-slate-500 dark:text-slate-500">Loading images, profiles, and networks…</p>
            )}
            {readyImages.length === 0 && !images.isLoading && (
              <p className="text-xs text-amber-700 dark:text-amber-400">
                No ready images. Register one under Images (status must be ready).
              </p>
            )}
            {profileNames.length === 0 && !profiles.isLoading && (
              <p className="text-xs text-amber-700 dark:text-amber-400">
                No cloud-init profiles. Create one under Cloud-init.
              </p>
            )}
            {networkNames.length === 0 && !networks.isLoading && (
              <p className="text-xs text-amber-700 dark:text-amber-400">No attachable networks found on this agent.</p>
            )}
            <label className="block text-sm">
              Name
              <input
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              Image
              <select
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
                value={imageName}
                onChange={(e) => setImageName(e.target.value)}
                required
                disabled={readyImages.length === 0}
              >
                <option value="">Select image…</option>
                {readyImages.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Cloud-init profile
              <select
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                value={cloudInitProfile}
                onChange={(e) => setCloudInitProfile(e.target.value)}
                required
                disabled={profileNames.length === 0}
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
              <select
                className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                value={network}
                onChange={(e) => setNetwork(e.target.value)}
                required
                disabled={networkNames.length === 0}
              >
                <option value="">Select network…</option>
                {networkNames.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block text-sm">
                vCPU
                <input
                  type="number"
                  min={1}
                  className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                  value={vcpu}
                  onChange={(e) => setVcpu(e.target.value)}
                />
              </label>
              <label className="block text-sm">
                Memory (MB)
                <input
                  type="number"
                  min={256}
                  className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
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
            <p className="text-xs text-slate-500 dark:text-slate-500">
              Power: {String(initial?.libvirt_state ?? "unknown")}. Hardware changes on a running VM
              need your confirmation before the agent reboots the guest.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <label className="block text-sm">
                vCPU
                <input
                  type="number"
                  min={1}
                  className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                  value={vcpu}
                  onChange={(e) => setVcpu(e.target.value)}
                />
              </label>
              <label className="block text-sm">
                Memory (MB)
                <input
                  type="number"
                  min={256}
                  className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
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
