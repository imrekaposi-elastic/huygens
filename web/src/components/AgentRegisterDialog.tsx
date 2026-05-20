import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import { AgentTechIcon, CloudIcon, GlobeIcon } from "@/components/icons/NavIcons";
import { flattenRegionTree } from "@/lib/regionTree";

type Props = {
  open: boolean;
  organizationId: string;
  onClose: () => void;
  onRegistered: () => void;
};

export function AgentRegisterDialog({ open, organizationId, onClose, onRegistered }: Props) {
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("https://127.0.0.1:8765");
  const [tlsVerify, setTlsVerify] = useState(false);
  const [infrastructureProviderId, setInfrastructureProviderId] = useState("");
  const [regionId, setRegionId] = useState("");
  const [agentTechnologyId, setAgentTechnologyId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [issuedToken, setIssuedToken] = useState<string | null>(null);
  const [connectionWarning, setConnectionWarning] = useState<string | null>(null);

  const { data: providers } = useQuery({
    queryKey: ["infrastructure-providers"],
    queryFn: () => api.infrastructureProviders(),
    enabled: open,
  });

  const { data: technologies } = useQuery({
    queryKey: ["agent-technologies"],
    queryFn: () => api.agentTechnologies(),
    enabled: open,
  });

  const { data: providerDetail } = useQuery({
    queryKey: ["infrastructure-provider", infrastructureProviderId],
    queryFn: () => api.infrastructureProvider(infrastructureProviderId),
    enabled: open && !!infrastructureProviderId,
  });

  const regionOptions = providerDetail
    ? flattenRegionTree(providerDetail.region_tree)
    : [];

  const enabledTechs = technologies?.filter((t) => t.platform_enabled) ?? [];

  useEffect(() => {
    if (!open) return;
    setIssuedToken(null);
    setConnectionWarning(null);
    setError(null);
  }, [open]);

  useEffect(() => {
    if (providers?.length && !infrastructureProviderId) {
      setInfrastructureProviderId(providers[0].id);
    }
  }, [providers, infrastructureProviderId]);

  useEffect(() => {
    if (enabledTechs.length && !agentTechnologyId) {
      setAgentTechnologyId(enabledTechs[0].id);
    }
  }, [enabledTechs, agentTechnologyId]);

  useEffect(() => {
    if (regionOptions.length) {
      setRegionId(regionOptions[0].id);
    } else {
      setRegionId("");
    }
  }, [providerDetail?.id, regionOptions.length]);

  if (!open) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!infrastructureProviderId || !regionId || !agentTechnologyId) {
      setError("Select infrastructure provider, region, and fabric.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await api.registerAgent({
        name: name.trim(),
        base_url: baseUrl.trim(),
        organization_id: organizationId,
        infrastructure_provider_id: infrastructureProviderId,
        region_id: regionId,
        agent_technology_id: agentTechnologyId,
        tls_verify: tlsVerify,
      });
      setIssuedToken(created.agent_token);
      setConnectionWarning(
        created.connection_status === "error" && created.last_poll_error
          ? created.last_poll_error
          : null,
      );
      onRegistered();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 dark:bg-black/60 p-4"
      role="dialog"
      aria-modal="true"
    >
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Register agent</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Each libvirt agent is enrolled on exactly one region. Coverage propagates to parent regions
          and to child regions under that node.
        </p>

        {issuedToken ? (
          <div className="mt-4 space-y-3">
            {connectionWarning && (
              <p className="rounded bg-amber-950/50 px-3 py-2 text-sm text-amber-200">
                Registered, but the platform could not reach the agent: {connectionWarning}
              </p>
            )}
            <p className="text-sm text-emerald-600 dark:text-emerald-400">Agent registered. Save this token:</p>
            <pre className="overflow-x-auto rounded-lg bg-slate-100 dark:bg-slate-950 p-3 text-xs text-amber-200">
              {issuedToken}
            </pre>
            <button
              type="button"
              onClick={onClose}
              className="min-h-11 w-full rounded-lg bg-emerald-600 font-medium hover:bg-emerald-500"
            >
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={submit} className="mt-4 space-y-3">
            {error && (
              <p className="rounded bg-red-50/90 dark:bg-red-950/50 px-3 py-2 text-sm text-red-700 dark:text-red-300">{error}</p>
            )}
            {(providers?.length ?? 0) === 0 && (
              <p className="text-sm text-amber-200">
                <Link to="/infrastructure" className="underline" onClick={onClose}>
                  Create an infrastructure provider and regions
                </Link>{" "}
                first.
              </p>
            )}
            <label className="block text-sm">
              <span className="mb-1 flex items-center gap-2">
                <AgentTechIcon className="size-4 shrink-0 text-slate-500 dark:text-slate-500" />
                Fabric
              </span>
              <select
                className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                value={agentTechnologyId}
                onChange={(e) => setAgentTechnologyId(e.target.value)}
              >
                {enabledTechs.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 flex items-center gap-2">
                <CloudIcon className="size-4 shrink-0 text-slate-500 dark:text-slate-500" />
                Infrastructure provider
              </span>
              <select
                className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                value={infrastructureProviderId}
                onChange={(e) => setInfrastructureProviderId(e.target.value)}
              >
                {providers?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                    {p.operational ? " (operational)" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 flex items-center gap-2">
                <GlobeIcon className="size-4 shrink-0 text-slate-500 dark:text-slate-500" />
                Region
              </span>
              <select
                className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
                value={regionId}
                onChange={(e) => setRegionId(e.target.value)}
                disabled={!regionOptions.length}
              >
                {regionOptions.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.label} {r.operational ? "· operational" : ""}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Agent name
              <input
                className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
            <label className="block text-sm">
              Base URL
              <input
                className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                placeholder="https://host.example:8765"
                required
              />
              <span className="mt-1 block text-xs text-slate-500 dark:text-slate-500">
                Libvirt agent listens on HTTPS port 8765 (not the dev proxy on 9080).
              </span>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={tlsVerify}
                onChange={(e) => setTlsVerify(e.target.checked)}
                className="size-4 rounded border-slate-300 dark:border-slate-600"
              />
              Verify TLS certificate (uncheck for self-signed certs)
            </label>
            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={onClose} className="min-h-11 rounded-lg border border-slate-300 dark:border-slate-600 px-4 text-sm">
                Cancel
              </button>
              <button
                type="submit"
                disabled={busy}
                className="min-h-11 rounded-lg bg-emerald-600 px-5 font-medium hover:bg-emerald-500 disabled:opacity-50"
              >
                {busy ? "Registering…" : "Register"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
