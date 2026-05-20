import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import { Modal } from "@/components/Modal";

type Props = {
  open: boolean;
  projectId: string;
  agentId: string;
  onClose: () => void;
  onSaved: () => void;
};

export function ImageDialog({ open, projectId, agentId, onClose, onSaved }: Props) {
  const [name, setName] = useState("");
  const [source, setSource] = useState("");
  const [sha256, setSha256] = useState("");
  const [fetch, setFetch] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setErr(null);
    setName("");
    setSource("");
    setSha256("");
    setFetch(true);
  }, [open]);

  const save = useMutation({
    mutationFn: () =>
      api.createImage(projectId, agentId, {
        name: name.trim(),
        source: source.trim(),
        sha256: sha256.trim() || undefined,
        fetch,
      }),
    onSuccess: () => {
      onSaved();
      onClose();
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Create failed"),
  });

  return (
    <Modal
      open={open}
      title="Register base image"
      onClose={onClose}
      footer={
        <>
          <button type="button" onClick={onClose} className="min-h-10 rounded-lg border border-slate-300 dark:border-slate-600 px-4 text-sm">
            Cancel
          </button>
          <button
            type="button"
            disabled={save.isPending || !name.trim() || !source.trim()}
            onClick={() => save.mutate()}
            className="min-h-10 rounded-lg bg-emerald-600 px-5 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            {save.isPending ? "Registering…" : "Register"}
          </button>
        </>
      }
    >
      <div className="space-y-3">
        {err && <p className="text-sm text-red-700 dark:text-red-300">{err}</p>}
        <p className="text-xs text-slate-500 dark:text-slate-500">
          Base disk images pair with cloud-init profiles when creating VMs. Source is an HTTP(S) URL
          or absolute path to a qcow2/raw file on the agent host.
        </p>
        <label className="block text-sm">
          Name
          <input
            className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="ubuntu-noble"
            pattern="[a-zA-Z0-9._-]+"
            required
          />
        </label>
        <label className="block text-sm">
          Source URL or path
          <input
            className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="https://…/noble-server-cloudimg-amd64.img"
            required
          />
        </label>
        <label className="block text-sm">
          SHA-256 (optional)
          <input
            className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-xs"
            value={sha256}
            onChange={(e) => setSha256(e.target.value)}
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={fetch} onChange={(e) => setFetch(e.target.checked)} />
          Download or copy immediately
        </label>
      </div>
    </Modal>
  );
}
