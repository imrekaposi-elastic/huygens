import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import { FileTextField } from "@/components/FileTextField";
import { Modal } from "@/components/Modal";

export type CloudInitProfile = {
  name: string;
  user_data: string;
  meta_data: string;
  network_config: string | null;
  ssh_keys?: string[];
};

const DEFAULT_META = "instance-id: local\n";
const DEFAULT_USER = `#cloud-config
ssh_pwauth: false
`;

type Props = {
  open: boolean;
  mode: "create" | "edit";
  projectId: string;
  agentId: string;
  initial?: CloudInitProfile | null;
  onClose: () => void;
  onSaved: () => void;
};

export function CloudInitDialog({
  open,
  mode,
  projectId,
  agentId,
  initial,
  onClose,
  onSaved,
}: Props) {
  const [name, setName] = useState("");
  const [userData, setUserData] = useState(DEFAULT_USER);
  const [metaData, setMetaData] = useState(DEFAULT_META);
  const [networkConfig, setNetworkConfig] = useState("");
  const [sshKeys, setSshKeys] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [validateOk, setValidateOk] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setErr(null);
    setValidateOk(null);
    if (mode === "edit" && initial) {
      setName(initial.name);
      setUserData(initial.user_data);
      setMetaData(initial.meta_data || DEFAULT_META);
      setNetworkConfig(initial.network_config ?? "");
      setSshKeys((initial.ssh_keys ?? []).join("\n"));
    } else {
      setName("");
      setUserData(DEFAULT_USER);
      setMetaData(DEFAULT_META);
      setNetworkConfig("");
      setSshKeys("");
    }
  }, [open, mode, initial]);

  const payload = () => ({
    user_data: userData,
    meta_data: metaData,
    network_config: networkConfig.trim() || null,
    ssh_keys: sshKeys
      .split("\n")
      .map((k) => k.trim())
      .filter(Boolean),
  });

  const validate = useMutation({
    mutationFn: () => api.validateCloudInit(projectId, agentId, payload()),
    onSuccess: (res) => {
      setValidateOk(res.message ?? "Valid");
      setErr(null);
    },
    onError: (e) => {
      setValidateOk(null);
      setErr(e instanceof ApiError ? e.message : "Validation failed");
    },
  });

  const save = useMutation({
    mutationFn: async () => {
      const body = { ...payload(), name: name.trim() };
      if (mode === "create") {
        return api.createCloudInitProfile(projectId, agentId, body);
      }
      return api.updateCloudInitProfile(projectId, agentId, initial!.name, {
        user_data: body.user_data,
        meta_data: body.meta_data,
        network_config: body.network_config,
        ssh_keys: body.ssh_keys,
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
      wide
      title={mode === "create" ? "New cloud-init profile" : `Edit ${initial?.name ?? "profile"}`}
      onClose={onClose}
      footer={
        <>
          <button
            type="button"
            onClick={onClose}
            className="min-h-10 rounded-lg border border-slate-600 px-4 text-sm"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={validate.isPending}
            onClick={() => validate.mutate()}
            className="min-h-10 rounded-lg border border-slate-600 px-4 text-sm text-slate-200 hover:bg-slate-800"
          >
            {validate.isPending ? "Validating…" : "Validate"}
          </button>
          <button
            type="button"
            disabled={save.isPending || (mode === "create" && !name.trim())}
            onClick={() => save.mutate()}
            className="min-h-10 rounded-lg bg-emerald-600 px-5 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            {save.isPending ? "Saving…" : "Save"}
          </button>
        </>
      }
    >
      <div className="space-y-4">
        {err && <p className="rounded bg-red-950/50 px-3 py-2 text-sm text-red-300">{err}</p>}
        {validateOk && (
          <p className="rounded bg-emerald-950/40 px-3 py-2 text-sm text-emerald-300">{validateOk}</p>
        )}
        {mode === "create" && (
          <label className="block text-sm">
            Profile name
            <input
              className="mt-1 w-full min-h-10 rounded-lg border border-slate-700 bg-slate-800 px-3 font-mono"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              pattern="^[a-zA-Z0-9._-]+$"
            />
          </label>
        )}
        <FileTextField
          label="user-data (#cloud-config)"
          hint="Required. First line should be #cloud-config."
          value={userData}
          onChange={setUserData}
          required
          rows={10}
        />
        <FileTextField
          label="meta-data"
          value={metaData}
          onChange={setMetaData}
          required
          rows={4}
        />
        <FileTextField
          label="network-config"
          hint="Optional. Version 2 network config YAML."
          value={networkConfig}
          onChange={setNetworkConfig}
          rows={6}
          placeholder="version: 2\nethernets: …"
        />
        <label className="block text-sm">
          SSH public keys (one per line, optional)
          <textarea
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs"
            value={sshKeys}
            onChange={(e) => setSshKeys(e.target.value)}
            rows={3}
          />
        </label>
      </div>
    </Modal>
  );
}
