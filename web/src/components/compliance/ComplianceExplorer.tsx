import { useMemo, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ComplianceExplorerRow, ComplianceItem } from "@/api/types";
import {
  ComplianceMembershipLegend,
  MembershipCheckbox,
} from "@/components/compliance/ComplianceMembershipLegend";
import {
  ComplianceResourceSearch,
  type ResourceSearchValue,
} from "@/components/compliance/ComplianceResourceSearch";

type Props = { organizationId: string };

const PAGE_SIZE = 25;

type FilterState = {
  catalogSlug: string;
  catalogMatch: "has" | "missing";
  traitKey: string;
  traitMatch: "has" | "missing";
  traitScope: "any" | "provider" | "region";
  resourceType: "" | "vm" | "network" | "project";
  resourceSearch: ResourceSearchValue;
};

const EMPTY_RESOURCE_SEARCH: ResourceSearchValue = {
  query: "",
  resourceKey: "",
  label: "",
};

const DEFAULT_FILTER: FilterState = {
  catalogSlug: "",
  catalogMatch: "missing",
  traitKey: "",
  traitMatch: "has",
  traitScope: "any",
  resourceType: "",
  resourceSearch: EMPTY_RESOURCE_SEARCH,
};

export function ComplianceExplorer({ organizationId }: Props) {
  const [filter, setFilter] = useState<FilterState>(DEFAULT_FILTER);
  const [applied, setApplied] = useState<FilterState>(DEFAULT_FILTER);
  const [page, setPage] = useState(0);

  const facets = useQuery({
    queryKey: ["compliance-explorer-facets", organizationId],
    queryFn: () => api.complianceExplorerFacets(organizationId),
  });

  const explorer = useQuery({
    queryKey: ["compliance-explorer", organizationId, applied, page],
    queryFn: () =>
      api.complianceExplorer(organizationId, {
        catalog_slug: applied.catalogSlug || undefined,
        catalog_match: applied.catalogSlug ? applied.catalogMatch : undefined,
        trait_key: applied.traitKey || undefined,
        trait_match: applied.traitKey ? applied.traitMatch : undefined,
        trait_scope: applied.traitScope,
        resource_type: applied.resourceType || undefined,
        q: applied.resourceSearch.resourceKey
          ? undefined
          : applied.resourceSearch.query.trim() || undefined,
        resource_key: applied.resourceSearch.resourceKey || undefined,
        offset: page * PAGE_SIZE,
        page_size: PAGE_SIZE,
      }),
    enabled: !!organizationId,
  });

  const presets = useMemo(() => {
    const items = facets.data?.catalog_items ?? [];
    const traits = facets.data?.trait_keys ?? [];
    const out: { label: string; apply: FilterState }[] = [];
    for (const item of items) {
      if (/bio/i.test(item.slug) || /bio/i.test(item.name)) {
        out.push({
          label: `Missing ${item.name}`,
          apply: {
            ...DEFAULT_FILTER,
            catalogSlug: item.slug,
            catalogMatch: "missing",
          },
        });
      }
    }
    for (const key of traits) {
      if (/eu|europe|sovereign/i.test(key)) {
        out.push({
          label: `Placed in ${key}`,
          apply: {
            ...DEFAULT_FILTER,
            traitKey: key,
            traitMatch: "has",
          },
        });
      }
    }
    if (!out.length && items[0]) {
      out.push({
        label: `Missing ${items[0].name}`,
        apply: { ...DEFAULT_FILTER, catalogSlug: items[0].slug, catalogMatch: "missing" },
      });
    }
    return out;
  }, [facets.data]);

  function applyFilter(next: FilterState) {
    setFilter(next);
    setApplied(next);
    setPage(0);
  }

  const total = explorer.data?.total_matched ?? 0;
  const offset = explorer.data?.offset ?? page * PAGE_SIZE;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const rangeStart = total === 0 ? 0 : offset + 1;
  const rangeEnd = Math.min(offset + PAGE_SIZE, total);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">Explorer</h2>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Drill down by catalog assignment (e.g. missing BIO) or placement traits (e.g. EU region).
        Search resources by name or project; pick a suggestion to jump straight to one workload.
      </p>
      <ComplianceMembershipLegend className="mt-2" compact showAggregate />

      {presets.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {presets.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => applyFilter(p.apply)}
              className="rounded-full border border-slate-300 px-3 py-1 text-xs hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-800"
            >
              {p.label}
            </button>
          ))}
          <button
            type="button"
            onClick={() => applyFilter(DEFAULT_FILTER)}
            className="rounded-full border border-slate-300 px-3 py-1 text-xs text-slate-500 dark:border-slate-600"
          >
            All workloads
          </button>
        </div>
      )}

      <form
        className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-3"
        onSubmit={(e) => {
          e.preventDefault();
          applyFilter(filter);
        }}
      >
        <ComplianceResourceSearch
          organizationId={organizationId}
          value={filter.resourceSearch}
          resourceType={filter.resourceType}
          onChange={(resourceSearch) => {
            setFilter((f) => {
              const next = { ...f, resourceSearch };
              if (resourceSearch.resourceKey) {
                setApplied(next);
                setPage(0);
              }
              return next;
            });
          }}
        />

        <label className="text-sm md:col-span-2">
          Catalog standard
          <select
            className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 dark:border-slate-700 dark:bg-slate-800"
            value={filter.catalogSlug}
            onChange={(e) => setFilter((f) => ({ ...f, catalogSlug: e.target.value }))}
          >
            <option value="">— Any —</option>
            {(facets.data?.catalog_items ?? []).map((i) => (
              <option key={i.id} value={i.slug}>
                {i.name} ({i.slug})
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Catalog match
          <select
            className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 dark:border-slate-700 dark:bg-slate-800"
            value={filter.catalogMatch}
            onChange={(e) =>
              setFilter((f) => ({
                ...f,
                catalogMatch: e.target.value as "has" | "missing",
              }))
            }
            disabled={!filter.catalogSlug}
          >
            <option value="missing">Missing assignment</option>
            <option value="has">Has assignment</option>
          </select>
        </label>
        <label className="text-sm">
          Placement trait contains
          <input
            className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 dark:border-slate-700 dark:bg-slate-800"
            value={filter.traitKey}
            onChange={(e) => setFilter((f) => ({ ...f, traitKey: e.target.value }))}
            placeholder="e.g. eu, bio, europe"
            list="trait-keys"
          />
          <datalist id="trait-keys">
            {(facets.data?.trait_keys ?? []).map((k) => (
              <option key={k} value={k} />
            ))}
          </datalist>
        </label>
        <label className="text-sm">
          Trait match
          <select
            className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 dark:border-slate-700 dark:bg-slate-800"
            value={filter.traitMatch}
            onChange={(e) =>
              setFilter((f) => ({ ...f, traitMatch: e.target.value as "has" | "missing" }))
            }
            disabled={!filter.traitKey}
          >
            <option value="has">Placed with trait</option>
            <option value="missing">Missing trait</option>
          </select>
        </label>
        <label className="text-sm">
          Trait scope
          <select
            className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 dark:border-slate-700 dark:bg-slate-800"
            value={filter.traitScope}
            onChange={(e) =>
              setFilter((f) => ({
                ...f,
                traitScope: e.target.value as FilterState["traitScope"],
              }))
            }
            disabled={!filter.traitKey}
          >
            <option value="any">Provider or region</option>
            <option value="region">Region only</option>
            <option value="provider">Provider only</option>
          </select>
        </label>
        <label className="text-sm">
          Resource type
          <select
            className="mt-1 w-full min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 dark:border-slate-700 dark:bg-slate-800"
            value={filter.resourceType}
            onChange={(e) =>
              setFilter((f) => ({
                ...f,
                resourceType: e.target.value as FilterState["resourceType"],
              }))
            }
          >
            <option value="">All</option>
            <option value="vm">VM</option>
            <option value="network">Network</option>
            <option value="project">Project</option>
          </select>
        </label>
        <div className="flex items-end md:col-span-2 lg:col-span-3">
          <button
            type="submit"
            className="min-h-10 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500"
          >
            Run filter
          </button>
        </div>
      </form>

      <div className="mt-4" id="compliance-explorer-results">
        {explorer.isLoading && !explorer.data && (
          <p className="text-sm text-slate-500">Loading resources…</p>
        )}
        {explorer.isError && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
            Explorer could not load resources. If you use Docker, ensure the compliance service is
            running and restart the web proxy after updates.
          </p>
        )}
        {explorer.data && (
          <>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              <strong>{explorer.data.total_matched}</strong> match
              {explorer.data.filter_description ? `: ${explorer.data.filter_description}` : ""}
            </p>
            {total > 0 && (
              <p className="mt-1 text-xs text-slate-500">
                Showing {rangeStart}–{rangeEnd} of {total}
              </p>
            )}
            {explorer.isFetching && (
              <p className="mt-1 text-xs text-slate-500">Refreshing…</p>
            )}
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-xs uppercase text-slate-500 dark:border-slate-700">
                    <th className="py-2 pr-3">Resource</th>
                    <th className="py-2 pr-3">Project</th>
                    <th className="py-2 pr-3">Placement</th>
                    <th className="py-2 pr-3">Catalog</th>
                    <th className="py-2">Open</th>
                  </tr>
                </thead>
                <tbody>
                  {explorer.data.rows.map((row) => (
                    <ExplorerRow key={rowKey(row)} row={row} />
                  ))}
                </tbody>
              </table>
              {explorer.data.rows.length === 0 && (
                <p className="py-6 text-center text-sm text-slate-500">No matching resources.</p>
              )}
            </div>

            {total > PAGE_SIZE && (
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                <button
                  type="button"
                  disabled={page <= 0 || explorer.isFetching}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  className="min-h-9 rounded border border-slate-300 px-3 text-sm disabled:opacity-40 dark:border-slate-600"
                >
                  Previous
                </button>
                <span className="text-xs text-slate-500">
                  Page {currentPage} of {pageCount}
                </span>
                <button
                  type="button"
                  disabled={page >= pageCount - 1 || explorer.isFetching}
                  onClick={() => setPage((p) => p + 1)}
                  className="min-h-9 rounded border border-slate-300 px-3 text-sm disabled:opacity-40 dark:border-slate-600"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

function rowKey(row: ComplianceExplorerRow) {
  return `${row.resource_type}:${row.project_id}:${row.agent_id ?? ""}:${row.name ?? ""}`;
}

/** Split direct vs inherited catalog rows for display (API fields or trait fallback). */
function catalogMembershipSplit(row: ComplianceExplorerRow): {
  direct: ComplianceItem[];
  inherited: ComplianceItem[];
  aggregate: ComplianceItem[];
} {
  const fromApiDirect = row.direct_catalog_items ?? [];
  const fromApiInherited = row.inherited_catalog_items ?? [];
  const fromApiAggregate = row.aggregate_catalog_items ?? [];
  if (
    fromApiDirect.length > 0 ||
    fromApiInherited.length > 0 ||
    fromApiAggregate.length > 0
  ) {
    const directIds = new Set(fromApiDirect.map((i) => i.id));
    const inheritedIds = new Set(
      fromApiInherited.filter((i) => !directIds.has(i.id)).map((i) => i.id),
    );
    return {
      direct: fromApiDirect,
      inherited: fromApiInherited.filter((i) => !directIds.has(i.id)),
      aggregate: fromApiAggregate.filter(
        (i) => !directIds.has(i.id) && !inheritedIds.has(i.id),
      ),
    };
  }
  const inheritedSlugs = new Set(row.inherited_traits.map((t) => t.trait_key.toLowerCase()));
  const all = row.catalog_items ?? [];
  const direct: ComplianceItem[] = [];
  const inherited: ComplianceItem[] = [];
  const aggregate: ComplianceItem[] = [];
  for (const item of all) {
    if (inheritedSlugs.has(item.slug.toLowerCase())) {
      inherited.push(item);
    } else if (row.resource_type === "project") {
      aggregate.push(item);
    } else {
      direct.push(item);
    }
  }
  return { direct, inherited, aggregate };
}

function ExplorerRow({ row }: { row: ComplianceExplorerRow }) {
  const {
    direct: directItems,
    inherited: inheritedOnly,
    aggregate: aggregateOnly,
  } = catalogMembershipSplit(row);

  const resourceLabel =
    row.resource_type === "project"
      ? row.project_name
        ? `Project ${row.project_name}`
        : "Project"
      : `${row.resource_type} ${row.name}`;
  const placement = [
    row.agent_name,
    row.region_name,
    ...row.inherited_traits.map((t) => `${t.trait_key} (${t.scope})`),
  ]
    .filter(Boolean)
    .join(" · ");

  const projectLink =
    row.resource_type === "vm"
      ? { to: "/projects/$projectId/vms" as const, params: { projectId: row.project_id } }
      : row.resource_type === "network"
        ? { to: "/projects/$projectId/networks" as const, params: { projectId: row.project_id } }
        : { to: "/projects/$projectId/compliance" as const, params: { projectId: row.project_id } };

  return (
    <tr className="border-b border-slate-100 dark:border-slate-800">
      <td className="py-2 pr-3 font-medium">{resourceLabel}</td>
      <td className="py-2 pr-3 text-slate-600 dark:text-slate-400">{row.project_name ?? row.project_id}</td>
      <td className="py-2 pr-3 text-xs text-slate-500">{placement || "—"}</td>
      <td className="py-2 pr-3">
        {directItems.length === 0 &&
        inheritedOnly.length === 0 &&
        aggregateOnly.length === 0 ? (
          <span className="text-xs text-amber-700 dark:text-amber-300">none</span>
        ) : (
          <ul className="space-y-1">
            {directItems.map((i) => (
              <li key={`direct-${i.id}`} className="flex items-center gap-1.5 text-xs">
                <MembershipCheckbox variant="direct" />
                <span>{i.name}</span>
              </li>
            ))}
            {inheritedOnly.map((i) => (
              <li
                key={`inherited-${i.id}`}
                className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400"
              >
                <MembershipCheckbox variant="inherited" />
                <span>{i.name}</span>
              </li>
            ))}
            {aggregateOnly.map((i) => (
              <li
                key={`aggregate-${i.id}`}
                className="flex items-center gap-1.5 text-xs text-blue-800 dark:text-blue-200"
              >
                <MembershipCheckbox variant="aggregate" />
                <span>{i.name}</span>
              </li>
            ))}
          </ul>
        )}
      </td>
      <td className="py-2">
        <Link
          to={projectLink.to}
          params={projectLink.params}
          className="text-xs text-emerald-700 hover:underline dark:text-emerald-300"
        >
          View
        </Link>
      </td>
    </tr>
  );
}
