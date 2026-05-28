import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { isValidOrgSlug, slugFromName } from "@/auth/setup";
import { useAuth } from "@/auth/AuthContext";
import { api, ApiError } from "@/api/client";
import { InfrastructureCompliancePanel } from "@/components/compliance/InfrastructureCompliancePanel";
import { InfrastructureCharacteristicsPanel } from "@/components/compliance/InfrastructureCharacteristicsPanel";
import { CloudIcon, GlobeIcon, PageTitle } from "@/components/icons/NavIcons";
import { RegionTreePanel } from "@/components/RegionTreePanel";

function ProviderDetail({
  providerId,
  organizationId,
}: {
  providerId: string;
  organizationId: string | null;
}) {
  const qc = useQueryClient();
  const [subName, setSubName] = useState("");
  const [subSlug, setSubSlug] = useState("");
  const [subSlugTouched, setSubSlugTouched] = useState(false);
  const [parentRegionId, setParentRegionId] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["infrastructure-provider", providerId],
    queryFn: () => api.infrastructureProvider(providerId),
  });

  const removeProvider = useMutation({
    mutationFn: () => api.deleteInfrastructureProvider(providerId),
    onSuccess: () => {
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["infrastructure-provider", providerId] });
      void qc.invalidateQueries({ queryKey: ["infrastructure-providers"] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Delete failed"),
  });

  const addRegion = useMutation({
    mutationFn: () =>
      api.createRegion(providerId, {
        name: subName.trim(),
        slug: subSlug.trim() || slugFromName(subName),
        parent_region_id: parentRegionId || null,
      }),
    onSuccess: () => {
      setSubName("");
      setSubSlug("");
      setSubSlugTouched(false);
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["infrastructure-provider", providerId] });
      void qc.invalidateQueries({ queryKey: ["infrastructure-providers"] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Failed"),
  });

  if (isLoading || !data) return <p className="text-slate-500 dark:text-slate-500">Loading tree…</p>;

  const regionOptions = flattenForParentSelect(data.region_tree);
  const canDeleteProvider = data.total_agents === 0 && data.region_tree.length === 0;

  return (
    <div className="mt-4 border-t border-slate-200 dark:border-slate-800 pt-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span
          className={`rounded px-2 py-0.5 text-xs ${
            data.operational ? "bg-emerald-950 text-emerald-700 dark:text-emerald-300" : "bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
          }`}
        >
          {data.operational ? "Provider operational" : "Not operational"}
        </span>
        <span className="text-xs text-slate-500 dark:text-slate-500">{data.total_agents} enrolled agent(s)</span>
        <button
          type="button"
          disabled={!canDeleteProvider || removeProvider.isPending}
          onClick={() => {
            if (!canDeleteProvider) return;
            if (window.confirm(`Delete provider "${data.name}"? This cannot be undone.`)) {
              removeProvider.mutate();
            }
          }}
          className="ml-auto rounded border border-red-300 px-2 py-1 text-xs text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-900/80 dark:text-red-300 dark:hover:bg-red-950/40"
          title={
            canDeleteProvider
              ? "Delete provider"
              : "Delete is only allowed when there are no regions and no enrolled agents"
          }
        >
          {removeProvider.isPending ? "Deleting…" : "Delete provider"}
        </button>
      </div>
      <h2 className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
        <GlobeIcon className="size-4 shrink-0 text-slate-500 dark:text-slate-500" />
        Regions
      </h2>
      {organizationId && (
        <>
          <InfrastructureCompliancePanel organizationId={organizationId} providerId={providerId} />
          <InfrastructureCharacteristicsPanel organizationId={organizationId} providerId={providerId} />
        </>
      )}
      <RegionTreePanel
        nodes={data.region_tree}
        infrastructureProviderId={providerId}
        organizationId={organizationId}
      />
      <form
        className="mt-4 flex flex-col gap-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/90 dark:bg-slate-900/50 p-4 md:flex-row md:flex-wrap md:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          addRegion.mutate();
        }}
      >
        <label className="flex items-center gap-2 text-sm md:w-full">
          <GlobeIcon className="size-4 shrink-0 text-slate-500 dark:text-slate-500" />
          <span className="flex-1">
          Parent region (optional — leave empty for top-level)
          <select
            className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
            value={parentRegionId}
            onChange={(e) => setParentRegionId(e.target.value)}
          >
            <option value="">— Top level —</option>
            {regionOptions.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </select>
          </span>
        </label>
        <label className="flex flex-1 items-center gap-2 text-sm">
          <GlobeIcon className="size-4 shrink-0 text-slate-500 dark:text-slate-500" />
          <span className="flex-1">
          Region name
          <input
            className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
            value={subName}
            onChange={(e) => {
              setSubName(e.target.value);
              if (!subSlugTouched) setSubSlug(slugFromName(e.target.value));
            }}
            required
          />
          </span>
        </label>
        <label className="flex-1 text-sm">
          Slug
          <input
            className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
            value={subSlug}
            onChange={(e) => {
              setSubSlugTouched(true);
              setSubSlug(e.target.value);
            }}
          />
        </label>
        <button
          type="submit"
          disabled={addRegion.isPending}
          className="min-h-11 rounded-lg bg-emerald-600 px-4 font-medium hover:bg-emerald-500"
        >
          Add region
        </button>
      </form>
      {err && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{err}</p>}
    </div>
  );
}

function flattenForParentSelect(
  nodes: import("@/api/types").RegionTreeNode[],
  depth = 0,
): { id: string; label: string }[] {
  const out: { id: string; label: string }[] = [];
  for (const n of nodes) {
    out.push({ id: n.id, label: `${"—".repeat(depth)} ${n.name}` });
    out.push(...flattenForParentSelect(n.children, depth + 1));
  }
  return out;
}

export function InfrastructureProvidersPage() {
  const { selectedOrgId } = useAuth();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const { data: providers, isLoading } = useQuery({
    queryKey: ["infrastructure-providers"],
    queryFn: () => api.infrastructureProviders(),
  });

  const create = useMutation({
    mutationFn: () => {
      const finalSlug = slug.trim() || slugFromName(name);
      if (!isValidOrgSlug(finalSlug)) throw new ApiError("Invalid slug", 400);
      return api.createInfrastructureProvider({ name: name.trim(), slug: finalSlug });
    },
    onSuccess: (p) => {
      setName("");
      setSlug("");
      setExpandedId(p.id);
      void qc.invalidateQueries({ queryKey: ["infrastructure-providers"] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Create failed"),
  });

  return (
    <div className="space-y-6">
      <div>
        <PageTitle icon={<CloudIcon />}>Infrastructure providers</PageTitle>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Functional vendors or estates (Hetzner, Azure, on-prem). Regions form a tree (datacenter →
          rack → …). Operational status propagates upward when a sub-region has an enrolled agent.
        </p>
      </div>

      <form
        className="flex flex-col gap-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 md:flex-row md:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <label className="flex-1 text-sm">
          Provider name
          <input
            className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              if (!slugTouched) setSlug(slugFromName(e.target.value));
            }}
            required
          />
        </label>
        <label className="flex-1 text-sm">
          Slug
          <input
            className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
            value={slug}
            onChange={(e) => {
              setSlugTouched(true);
              setSlug(e.target.value);
            }}
          />
        </label>
        <button
          type="submit"
          disabled={create.isPending}
          className="min-h-11 rounded-lg bg-emerald-600 px-4 font-medium hover:bg-emerald-500"
        >
          Add provider
        </button>
      </form>
      {err && <p className="text-sm text-red-600 dark:text-red-400">{err}</p>}

      {isLoading && <p className="text-slate-600 dark:text-slate-400">Loading…</p>}
      <div className="space-y-3">
        {providers?.map((p) => (
          <section key={p.id} className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
            <button
              type="button"
              className="flex w-full items-center justify-between text-left"
              onClick={() => setExpandedId(expandedId === p.id ? null : p.id)}
            >
              <div className="flex min-w-0 items-center gap-2">
                <CloudIcon className="size-4 shrink-0 text-slate-500 dark:text-slate-500" />
                <span className="text-lg font-medium">{p.name}</span>
                <span className="font-mono text-sm text-slate-500 dark:text-slate-500">{p.slug}</span>
              </div>
              <span
                className={`rounded px-2 py-0.5 text-xs ${
                  p.operational ? "bg-emerald-950 text-emerald-700 dark:text-emerald-300" : "bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                }`}
              >
                {p.operational ? "operational" : "inactive"}
              </span>
            </button>
            {expandedId === p.id && (
              <ProviderDetail providerId={p.id} organizationId={selectedOrgId} />
            )}
          </section>
        ))}
      </div>
    </div>
  );
}
