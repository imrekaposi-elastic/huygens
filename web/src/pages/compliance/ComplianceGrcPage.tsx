import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { ComplianceControl, ComplianceStandard } from "@/api/types";
import { useAuth } from "@/auth/AuthContext";
import { canManageComplianceCatalog } from "@/auth/permissions";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-lg font-medium text-slate-800 dark:text-slate-100">{children}</h2>;
}

export function ComplianceGrcPage() {
  const { user, selectedOrgId } = useAuth();
  const organizationId = selectedOrgId ?? "";
  const platformAdmin = isPlatformAdmin(getAccessToken());
  const canManage = canManageComplianceCatalog(user, organizationId, platformAdmin);
  const qc = useQueryClient();

  const [err, setErr] = useState<string | null>(null);
  const [selectedStandardId, setSelectedStandardId] = useState<string | null>(null);
  const [editingStandard, setEditingStandard] = useState(false);
  const [standardPane, setStandardPane] = useState<"controls" | "cycles">("controls");

  const standards = useQuery({
    queryKey: ["grc-standards", organizationId],
    queryFn: () => api.listComplianceStandards(organizationId),
    enabled: !!organizationId,
  });

  const selectedStandard: ComplianceStandard | null = useMemo(() => {
    const list = standards.data ?? [];
    return list.find((s) => s.id === selectedStandardId) ?? (list[0] ?? null);
  }, [standards.data, selectedStandardId]);

  // standard selection currently only sets the id; pane defaults to Controls.

  const controls = useQuery({
    queryKey: ["grc-controls", organizationId, selectedStandard?.id],
    queryFn: () => api.listComplianceControls(organizationId, selectedStandard!.id),
    enabled: !!organizationId && !!selectedStandard?.id,
  });

  const cycles = useQuery({
    queryKey: ["grc-cycles", organizationId, selectedStandard?.id],
    queryFn: () => api.listComplianceCycles(organizationId, selectedStandard!.id),
    enabled: !!organizationId && !!selectedStandard?.id,
  });

  const packs = useQuery({
    queryKey: ["grc-packs", organizationId],
    queryFn: () => api.listCompliancePacks(organizationId),
    enabled: !!organizationId,
  });

  const characteristics = useQuery({
    queryKey: ["grc-characteristics", organizationId],
    queryFn: () => api.listQualitativeCharacteristics(organizationId),
    enabled: !!organizationId,
  });

  const [newStandardName, setNewStandardName] = useState("");
  const [standardEditName, setStandardEditName] = useState("");
  const [standardEditDescription, setStandardEditDescription] = useState("");
  const createStandard = useMutation({
    mutationFn: () =>
      api.createComplianceStandard(organizationId, {
        name: newStandardName.trim(),
      }),
    onSuccess: (created) => {
      setNewStandardName("");
      setErr(null);
      setSelectedStandardId(created.id);
      void qc.invalidateQueries({ queryKey: ["grc-standards", organizationId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Create standard failed"),
  });

  const updateStandard = useMutation({
    mutationFn: () =>
      api.updateComplianceStandard(organizationId, selectedStandard!.id, {
        name: standardEditName.trim() || undefined,
        description: standardEditDescription.trim() || null,
      }),
    onSuccess: () => {
      setErr(null);
      setEditingStandard(false);
      void qc.invalidateQueries({ queryKey: ["grc-standards", organizationId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Update standard failed"),
  });

  const deleteStandard = useMutation({
    mutationFn: () => api.deleteComplianceStandard(organizationId, selectedStandard!.id),
    onSuccess: () => {
      setErr(null);
      setEditingStandard(false);
      setSelectedStandardId(null);
      void qc.invalidateQueries({ queryKey: ["grc-standards", organizationId] });
      void qc.invalidateQueries({ queryKey: ["grc-controls", organizationId] });
      void qc.invalidateQueries({ queryKey: ["grc-cycles", organizationId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Delete standard failed"),
  });

  const [newControlName, setNewControlName] = useState("");
  const [newControlCode, setNewControlCode] = useState("");
  const createControl = useMutation({
    mutationFn: () =>
      api.createComplianceControl(organizationId, selectedStandard!.id, {
        control_code: newControlCode.trim() || null,
        name: newControlName.trim(),
      }),
    onSuccess: () => {
      setNewControlName("");
      setNewControlCode("");
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["grc-controls", organizationId, selectedStandard?.id] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Create control failed"),
  });

  const [newCycleName, setNewCycleName] = useState("");
  const createCycle = useMutation({
    mutationFn: () => api.createComplianceCycle(organizationId, selectedStandard!.id, { name: newCycleName.trim() }),
    onSuccess: () => {
      setNewCycleName("");
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["grc-cycles", organizationId, selectedStandard?.id] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Create cycle failed"),
  });

  const [packJson, setPackJson] = useState("");
  const [packValidation, setPackValidation] = useState<import("@/api/types").CompliancePackValidate | null>(null);
  const importPack = useMutation({
    mutationFn: async () => {
      const payload = JSON.parse(packJson) as unknown;
      const name = (payload as { name?: string }).name ?? "Imported pack";
      const pack_key = (payload as { pack_key?: string }).pack_key ?? `pack-${Date.now()}`;
      return api.importCompliancePack(organizationId, { pack_key, name, payload });
    },
    onSuccess: () => {
      setErr(null);
      setPackValidation(null);
      void qc.invalidateQueries({ queryKey: ["grc-packs", organizationId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Import pack failed"),
  });

  const validatePack = useMutation({
    mutationFn: async () => {
      const payload = JSON.parse(packJson) as unknown;
      const name = (payload as { name?: string }).name ?? "Imported pack";
      const pack_key = (payload as { pack_key?: string }).pack_key ?? `pack-${Date.now()}`;
      return api.validateCompliancePack(organizationId, { pack_key, name, payload });
    },
    onSuccess: (res) => {
      setErr(null);
      setPackValidation(res);
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Pack validation failed"),
  });

  const exportPdf = useMutation({
    mutationFn: () =>
      api.exportCompliancePdf(organizationId, {
        export_type: "pdf",
        standard_id: selectedStandard?.id ?? null,
        cycle_id: null,
      }),
    onSuccess: ({ blob, filename }) => {
      setErr(null);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename ?? "compliance-export.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "PDF export failed"),
  });

  const [newCharacteristicName, setNewCharacteristicName] = useState("");
  const [newCharacteristicDescription, setNewCharacteristicDescription] = useState("");
  const [newCharacteristicMoscow, setNewCharacteristicMoscow] =
    useState<import("@/api/types").MoscowKind>("should");
  const [newCharacteristicKind, setNewCharacteristicKind] = useState("placement");
  const [editingCharacteristicId, setEditingCharacteristicId] = useState<string | null>(null);
  const [editCharacteristicName, setEditCharacteristicName] = useState("");
  const [editCharacteristicDescription, setEditCharacteristicDescription] = useState("");
  const [editCharacteristicMoscow, setEditCharacteristicMoscow] =
    useState<import("@/api/types").MoscowKind>("should");
  const [editCharacteristicKind, setEditCharacteristicKind] = useState("placement");

  const createCharacteristic = useMutation({
    mutationFn: () =>
      api.createQualitativeCharacteristic(organizationId, {
        name: newCharacteristicName.trim(),
        description: newCharacteristicDescription.trim() || null,
        moscow: newCharacteristicMoscow,
        kind: newCharacteristicKind,
      }),
    onSuccess: () => {
      setNewCharacteristicName("");
      setNewCharacteristicDescription("");
      setNewCharacteristicMoscow("should");
      setNewCharacteristicKind("placement");
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["grc-characteristics", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-explorer-facets", organizationId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Create characteristic failed"),
  });

  const updateCharacteristic = useMutation({
    mutationFn: () =>
      api.updateQualitativeCharacteristic(organizationId, editingCharacteristicId!, {
        name: editCharacteristicName.trim() || undefined,
        description: editCharacteristicDescription.trim() || null,
        moscow: editCharacteristicMoscow,
        kind: editCharacteristicKind,
      }),
    onSuccess: () => {
      setEditingCharacteristicId(null);
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["grc-characteristics", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-explorer-facets", organizationId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Update characteristic failed"),
  });

  const deleteCharacteristic = useMutation({
    mutationFn: (id: string) => api.deleteQualitativeCharacteristic(organizationId, id),
    onSuccess: () => {
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["grc-characteristics", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-explorer-facets", organizationId] });
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Delete characteristic failed"),
  });

  const migrateLegacyTraits = useMutation({
    mutationFn: () => api.migrateLegacyTraitsToCharacteristics(organizationId),
    onSuccess: (res) => {
      setErr(null);
      void qc.invalidateQueries({ queryKey: ["grc-characteristics", organizationId] });
      void qc.invalidateQueries({ queryKey: ["compliance-explorer-facets", organizationId] });
      window.alert(
        `Migrated ${res.provider_traits_seen} provider and ${res.region_traits_seen} region legacy traits. ` +
          `Created ${res.characteristics_created} characteristics; added ${res.provider_links_added} provider and ` +
          `${res.region_links_added} region links.`,
      );
    },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Legacy trait migration failed"),
  });

  function beginEditCharacteristic(c: import("@/api/types").QualitativeCharacteristic) {
    setEditingCharacteristicId(c.id);
    setEditCharacteristicName(c.name);
    setEditCharacteristicDescription(c.description ?? "");
    setEditCharacteristicMoscow(c.moscow);
    setEditCharacteristicKind(c.kind);
  }

  function beginEditStandard() {
    if (!selectedStandard) return;
    setStandardEditName(selectedStandard.name);
    setStandardEditDescription(selectedStandard.description ?? "");
    setEditingStandard(true);
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <SectionTitle>GRC</SectionTitle>
          {!canManage && (
            <p className="text-xs text-slate-500">
              Create/edit requires <strong>admin</strong> or <strong>compliance_admin</strong>.
            </p>
          )}
        </div>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Standards, controls, evidence, cycles, packs, and PDF export. Evidence is stored outside the database and
          referenced from PostgreSQL.
        </p>
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <SectionTitle>Standards</SectionTitle>
          {standards.isLoading && <p className="mt-2 text-sm text-slate-500">Loading…</p>}
          <ul className="mt-3 space-y-1">
            {(standards.data ?? []).map((s) => {
              const active = (selectedStandard?.id ?? null) === s.id;
              return (
                <li key={s.id}>
                  <button
                    type="button"
                    className={`w-full rounded-lg px-3 py-2 text-left text-sm ${
                      active
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-200"
                        : "hover:bg-slate-50 dark:hover:bg-slate-800"
                    }`}
                    onClick={() => {
                      setSelectedStandardId(s.id);
                      setEditingStandard(false);
                    }}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{s.name}</span>
                      <span className="font-mono text-xs text-slate-500">{s.slug}</span>
                    </div>
                  </button>
                </li>
              );
            })}
            {!standards.data?.length && (
              <li className="text-sm text-slate-500">No standards yet. Create one to start.</li>
            )}
          </ul>

          {canManage && (
            <form
              className="mt-4 flex gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                createStandard.mutate();
              }}
            >
              <input
                className="min-h-10 flex-1 rounded-lg border border-slate-300 bg-slate-50 px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
                placeholder="New standard name"
                value={newStandardName}
                onChange={(e) => setNewStandardName(e.target.value)}
                required
              />
              <button
                type="submit"
                disabled={createStandard.isPending}
                className="min-h-10 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500"
              >
                Add
              </button>
            </form>
          )}
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900 lg:col-span-2">
          <SectionTitle>Standard details</SectionTitle>
          {!selectedStandard && <p className="mt-2 text-sm text-slate-500">Select a standard.</p>}
          {selectedStandard && (
            <div className="mt-3 space-y-5">
              <div className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{selectedStandard.name}</p>
                    {selectedStandard.description && !editingStandard && (
                      <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
                        {selectedStandard.description}
                      </p>
                    )}
                  </div>
                  {canManage && (
                    <div className="flex flex-wrap items-center gap-2">
                      {!editingStandard && (
                        <>
                          <button
                            type="button"
                            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
                            onClick={() => beginEditStandard()}
                          >
                            Edit standard
                          </button>
                          <button
                            type="button"
                            className="rounded-lg border border-red-300 px-3 py-1.5 text-xs text-red-700 hover:bg-red-50 dark:border-red-900/80 dark:text-red-300 dark:hover:bg-red-950/40"
                            onClick={() => {
                              if (window.confirm(`Delete standard "${selectedStandard.name}"?`)) {
                                deleteStandard.mutate();
                              }
                            }}
                            disabled={deleteStandard.isPending}
                          >
                            {deleteStandard.isPending ? "Deleting…" : "Delete"}
                          </button>
                          <button
                            type="button"
                            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
                            onClick={() => exportPdf.mutate()}
                            disabled={exportPdf.isPending || !selectedStandard}
                          >
                            {exportPdf.isPending ? "Exporting PDF…" : "Export PDF"}
                          </button>
                        </>
                      )}
                      {editingStandard && (
                        <>
                          <button
                            type="button"
                            className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
                            onClick={() => updateStandard.mutate()}
                            disabled={updateStandard.isPending}
                          >
                            {updateStandard.isPending ? "Saving…" : "Save"}
                          </button>
                          <button
                            type="button"
                            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
                            onClick={() => setEditingStandard(false)}
                          >
                            Cancel
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
                {editingStandard && (
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    <label className="text-xs">
                      Name
                      <input
                        className="mt-1 w-full min-h-9 rounded border border-slate-300 bg-slate-50 px-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                        value={standardEditName}
                        onChange={(e) => setStandardEditName(e.target.value)}
                      />
                    </label>
                    <label className="text-xs md:col-span-2">
                      Description
                      <textarea
                        className="mt-1 w-full rounded border border-slate-300 bg-slate-50 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
                        value={standardEditDescription}
                        onChange={(e) => setStandardEditDescription(e.target.value)}
                        rows={2}
                      />
                    </label>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2 dark:border-slate-800">
                {(
                  [
                    { id: "controls", label: "Controls" },
                    { id: "cycles", label: "Cycles (recurrence)" },
                  ] as const
                ).map((t) => {
                  const active = standardPane === t.id;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setStandardPane(t.id)}
                      className={`rounded-lg px-3 py-2 text-sm font-medium ${
                        active
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-200"
                          : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
                      }`}
                    >
                      {t.label}
                    </button>
                  );
                })}
              </div>

              {standardPane === "controls" && (
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Controls are the concrete requirements under this standard. Evidence attaches to a control.
                  </p>
                  {controls.isLoading && <p className="mt-2 text-sm text-slate-500">Loading…</p>}
                  <ul className="mt-3 space-y-2">
                    {(controls.data ?? []).map((c) => (
                      <ControlRow
                        key={c.id}
                        organizationId={organizationId}
                        control={c}
                        canManage={canManage}
                        onError={setErr}
                        onChanged={() => {
                          void qc.invalidateQueries({
                            queryKey: ["grc-controls", organizationId, selectedStandard.id],
                          });
                        }}
                      />
                    ))}
                    {!controls.data?.length && (
                      <li className="text-sm text-slate-500">No controls yet. Add one below.</li>
                    )}
                  </ul>
                  {canManage && (
                    <form
                      className="mt-4 flex flex-col gap-2 sm:flex-row"
                      onSubmit={(e) => {
                        e.preventDefault();
                        createControl.mutate();
                      }}
                    >
                      <input
                        className="min-h-10 flex-1 rounded-lg border border-slate-300 bg-slate-50 px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
                        placeholder="Control name"
                        value={newControlName}
                        onChange={(e) => setNewControlName(e.target.value)}
                        required
                      />
                      <input
                        className="min-h-10 w-40 rounded-lg border border-slate-300 bg-slate-50 px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
                        placeholder="Code"
                        value={newControlCode}
                        onChange={(e) => setNewControlCode(e.target.value)}
                      />
                      <button
                        type="submit"
                        disabled={createControl.isPending}
                        className="min-h-10 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500"
                      >
                        Add control
                      </button>
                    </form>
                  )}
                </div>
              )}

              {standardPane === "cycles" && (
                <div>
                  <p className="text-sm text-slate-500 dark:text-slate-400">
                    Cycles represent recurring review windows (annual, quarterly, etc.). Use them to track which period
                    evidence applies to.
                  </p>
                  {cycles.isLoading && <p className="mt-2 text-sm text-slate-500">Loading…</p>}
                  <ul className="mt-3 space-y-2">
                    {(cycles.data ?? []).map((cy) => (
                      <CycleRow
                        key={cy.id}
                        organizationId={organizationId}
                        cycle={cy}
                        canManage={canManage}
                        onError={setErr}
                        onChanged={() => {
                          void qc.invalidateQueries({
                            queryKey: ["grc-cycles", organizationId, selectedStandard.id],
                          });
                        }}
                      />
                    ))}
                    {!cycles.data?.length && (
                      <li className="text-sm text-slate-500">No cycles yet. Create one below.</li>
                    )}
                  </ul>
                  {canManage && (
                    <form
                      className="mt-4 flex gap-2"
                      onSubmit={(e) => {
                        e.preventDefault();
                        createCycle.mutate();
                      }}
                    >
                      <input
                        className="min-h-10 flex-1 rounded-lg border border-slate-300 bg-slate-50 px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
                        placeholder="Cycle name (e.g. 2026 annual review)"
                        value={newCycleName}
                        onChange={(e) => setNewCycleName(e.target.value)}
                        required
                      />
                      <button
                        type="submit"
                        disabled={createCycle.isPending}
                        className="min-h-10 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500"
                      >
                        Add cycle
                      </button>
                    </form>
                  )}
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <SectionTitle>Packs</SectionTitle>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Import a JSON compliance pack to seed a standard/control catalog (implementation evolves in later increments).
        </p>
        <div className="mt-3 grid gap-4 md:grid-cols-2">
          <div>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Imported</p>
            <ul className="mt-2 space-y-2 text-sm">
              {(packs.data ?? []).map((p) => (
                <li key={p.id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{p.name}</span>
                    <span className="font-mono text-xs text-slate-500">{p.pack_key}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    {p.vendor ?? "unknown vendor"} · {p.version ?? "unversioned"}
                  </p>
                </li>
              ))}
              {!packs.data?.length && <li className="text-sm text-slate-500">No packs imported yet.</li>}
            </ul>
          </div>
          <div>
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">Import</p>
            <textarea
              className="mt-2 h-40 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-xs font-mono dark:border-slate-700 dark:bg-slate-800"
              placeholder='{"pack_key":"iso27001:2022","name":"ISO 27001:2022",...}'
              value={packJson}
              onChange={(e) => setPackJson(e.target.value)}
            />
            {packValidation && (
              <div className="mt-2 rounded-lg border border-slate-200 bg-white p-2 text-xs dark:border-slate-800 dark:bg-slate-900">
                <p className="font-medium text-slate-700 dark:text-slate-300">Dry-run</p>
                <p className="mt-1 text-slate-600 dark:text-slate-400">
                  Would create {packValidation.standards_to_create} standards and {packValidation.controls_to_create} controls.
                </p>
                {!!packValidation.errors.length && (
                  <ul className="mt-1 list-disc pl-4 text-red-600 dark:text-red-400">
                    {packValidation.errors.slice(0, 5).map((e) => (
                      <li key={e}>{e}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                disabled={!canManage || validatePack.isPending || !packJson.trim()}
                onClick={() => validatePack.mutate()}
                className="min-h-10 rounded-lg border border-slate-300 px-4 text-sm dark:border-slate-700 disabled:opacity-50"
              >
                {validatePack.isPending ? "Validating…" : "Dry-run validate"}
              </button>
              <button
                type="button"
                className="min-h-10 rounded-lg border border-slate-300 px-4 text-sm dark:border-slate-700"
                onClick={() => setPackJson("")}
              >
                Clear
              </button>
              <button
                type="button"
                disabled={
                  !canManage ||
                  importPack.isPending ||
                  !packJson.trim() ||
                  !!packValidation?.errors.length
                }
                onClick={() => importPack.mutate()}
                className="min-h-10 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
              >
                {importPack.isPending ? "Importing…" : "Apply import"}
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <SectionTitle>Qualitative characteristics</SectionTitle>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Org-defined placement labels (MoSCoW, description) attachable on Infrastructure → provider/region. Inherited
          to workloads and searchable in Explorer. Legacy free-form traits are deprecated — migrate them here.
        </p>
        {canManage && (
          <button
            type="button"
            className="mt-2 rounded-lg border border-slate-300 px-3 py-1.5 text-xs hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
            disabled={migrateLegacyTraits.isPending}
            onClick={() => migrateLegacyTraits.mutate()}
          >
            {migrateLegacyTraits.isPending ? "Migrating…" : "Migrate legacy traits"}
          </button>
        )}
        <ul className="mt-3 space-y-2 text-sm">
          {(characteristics.data ?? []).map((c) => {
            const editing = editingCharacteristicId === c.id;
            return (
              <li key={c.id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                {editing ? (
                  <div className="space-y-2">
                    <input
                      className="w-full min-h-9 rounded-lg border border-slate-300 bg-slate-50 px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
                      value={editCharacteristicName}
                      onChange={(e) => setEditCharacteristicName(e.target.value)}
                    />
                    <textarea
                      className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                      rows={2}
                      placeholder="Description"
                      value={editCharacteristicDescription}
                      onChange={(e) => setEditCharacteristicDescription(e.target.value)}
                    />
                    <div className="flex flex-wrap gap-2">
                      <select
                        className="min-h-9 rounded-lg border border-slate-300 bg-slate-50 px-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                        value={editCharacteristicMoscow}
                        onChange={(e) =>
                          setEditCharacteristicMoscow(e.target.value as import("@/api/types").MoscowKind)
                        }
                      >
                        <option value="must">must</option>
                        <option value="should">should</option>
                        <option value="could">could</option>
                        <option value="wont">wont</option>
                      </select>
                      <select
                        className="min-h-9 rounded-lg border border-slate-300 bg-slate-50 px-2 text-sm dark:border-slate-700 dark:bg-slate-800"
                        value={editCharacteristicKind}
                        onChange={(e) => setEditCharacteristicKind(e.target.value)}
                      >
                        <option value="placement">placement</option>
                        <option value="policy">policy</option>
                        <option value="other">other</option>
                      </select>
                      <button
                        type="button"
                        className="rounded-lg bg-emerald-600 px-3 py-1 text-xs font-medium text-white hover:bg-emerald-500"
                        disabled={updateCharacteristic.isPending}
                        onClick={() => updateCharacteristic.mutate()}
                      >
                        Save
                      </button>
                      <button
                        type="button"
                        className="rounded-lg border border-slate-300 px-3 py-1 text-xs dark:border-slate-700"
                        onClick={() => setEditingCharacteristicId(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-medium">{c.name}</p>
                      <p className="mt-0.5 font-mono text-xs text-slate-500">{c.slug}</p>
                      {c.description && (
                        <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{c.description}</p>
                      )}
                      <p className="mt-1 text-xs text-slate-500">
                        {c.moscow} · {c.kind}
                      </p>
                    </div>
                    {canManage && (
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="text-xs text-emerald-700 hover:underline dark:text-emerald-300"
                          onClick={() => beginEditCharacteristic(c)}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          className="text-xs text-red-700 hover:underline dark:text-red-300"
                          disabled={deleteCharacteristic.isPending}
                          onClick={() => {
                            if (window.confirm(`Delete characteristic "${c.name}"?`)) {
                              deleteCharacteristic.mutate(c.id);
                            }
                          }}
                        >
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </li>
            );
          })}
          {!characteristics.data?.length && <li className="text-sm text-slate-500">No characteristics yet.</li>}
        </ul>
        {canManage && (
          <form
            className="mt-3 space-y-2"
            onSubmit={(e) => {
              e.preventDefault();
              createCharacteristic.mutate();
            }}
          >
            <input
              className="w-full min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
              placeholder="Name"
              value={newCharacteristicName}
              onChange={(e) => setNewCharacteristicName(e.target.value)}
              required
            />
            <textarea
              className="w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800"
              rows={2}
              placeholder="Description (optional)"
              value={newCharacteristicDescription}
              onChange={(e) => setNewCharacteristicDescription(e.target.value)}
            />
            <div className="flex flex-wrap gap-2">
              <select
                className="min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
                value={newCharacteristicMoscow}
                onChange={(e) => setNewCharacteristicMoscow(e.target.value as import("@/api/types").MoscowKind)}
              >
                <option value="must">must</option>
                <option value="should">should</option>
                <option value="could">could</option>
                <option value="wont">wont</option>
              </select>
              <select
                className="min-h-10 rounded-lg border border-slate-300 bg-slate-50 px-3 text-sm dark:border-slate-700 dark:bg-slate-800"
                value={newCharacteristicKind}
                onChange={(e) => setNewCharacteristicKind(e.target.value)}
              >
                <option value="placement">placement</option>
                <option value="policy">policy</option>
                <option value="other">other</option>
              </select>
              <button
                type="submit"
                disabled={createCharacteristic.isPending}
                className="min-h-10 rounded-lg bg-emerald-600 px-4 text-sm font-medium text-white hover:bg-emerald-500"
              >
                Add characteristic
              </button>
            </div>
          </form>
        )}
      </section>

      {err && <p className="text-sm text-red-600 dark:text-red-400">{err}</p>}
    </div>
  );
}

function ControlRow({
  organizationId,
  control,
  canManage,
  onError,
  onChanged,
}: {
  organizationId: string;
  control: ComplianceControl;
  canManage: boolean;
  onError: (msg: string | null) => void;
  onChanged: () => void;
}) {
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(control.name);
  const [code, setCode] = useState(control.control_code ?? "");
  const [description, setDescription] = useState(control.description ?? "");

  const update = useMutation({
    mutationFn: () =>
      api.updateComplianceControl(organizationId, control.id, {
        name: name.trim() || undefined,
        control_code: code.trim() || null,
        description: description.trim() || null,
      }),
    onSuccess: () => {
      setEditing(false);
      onError(null);
      onChanged();
    },
    onError: (e) => onError(e instanceof ApiError ? e.message : "Update control failed"),
  });

  const remove = useMutation({
    mutationFn: () => api.deleteComplianceControl(organizationId, control.id),
    onSuccess: () => {
      onError(null);
      onChanged();
      void qc.invalidateQueries({ queryKey: ["grc-evidence", organizationId, control.id] });
    },
    onError: (e) => onError(e instanceof ApiError ? e.message : "Delete control failed"),
  });

  return (
    <li className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium">
            {control.control_code ? (
              <span className="mr-2 font-mono text-xs">{control.control_code}</span>
            ) : null}
            {control.name}
          </p>
          {control.description && !editing && (
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{control.description}</p>
          )}
        </div>
        {canManage && (
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {!editing ? (
              <>
                <button
                  type="button"
                  className="text-xs text-emerald-700 hover:underline dark:text-emerald-300"
                  onClick={() => {
                    setName(control.name);
                    setCode(control.control_code ?? "");
                    setDescription(control.description ?? "");
                    setEditing(true);
                  }}
                >
                  Edit
                </button>
                <button
                  type="button"
                  className="text-xs text-red-600 hover:underline dark:text-red-400"
                  disabled={remove.isPending}
                  onClick={() => {
                    if (window.confirm(`Delete control "${control.name}"?`)) remove.mutate();
                  }}
                >
                  Delete
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  className="text-xs text-emerald-700 hover:underline dark:text-emerald-300"
                  disabled={update.isPending}
                  onClick={() => update.mutate()}
                >
                  {update.isPending ? "Saving…" : "Save"}
                </button>
                <button
                  type="button"
                  className="text-xs text-slate-600 hover:underline dark:text-slate-400"
                  onClick={() => setEditing(false)}
                >
                  Cancel
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {editing && (
        <div className="mt-2 grid gap-2 md:grid-cols-2">
          <label className="text-xs">
            Name
            <input
              className="mt-1 w-full min-h-9 rounded border border-slate-300 bg-slate-50 px-2 text-sm dark:border-slate-700 dark:bg-slate-800"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="text-xs">
            Code
            <input
              className="mt-1 w-full min-h-9 rounded border border-slate-300 bg-slate-50 px-2 text-sm dark:border-slate-700 dark:bg-slate-800"
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
          </label>
          <label className="text-xs md:col-span-2">
            Description
            <textarea
              className="mt-1 w-full rounded border border-slate-300 bg-slate-50 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </label>
        </div>
      )}

      <ControlEvidencePanel
        organizationId={organizationId}
        controlId={control.id}
        canManage={canManage}
      />
    </li>
  );
}

function CycleRow({
  organizationId,
  cycle,
  canManage,
  onError,
  onChanged,
}: {
  organizationId: string;
  cycle: import("@/api/types").ComplianceCycle;
  canManage: boolean;
  onError: (msg: string | null) => void;
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(cycle.name);
  const [status, setStatus] = useState(cycle.status);
  const [showStatus, setShowStatus] = useState(false);

  const cycleStatus = useQuery({
    queryKey: ["grc-cycle-status", organizationId, cycle.id],
    queryFn: () => api.getComplianceCycleStatus(organizationId, cycle.id),
    enabled: !!organizationId && showStatus,
  });

  const update = useMutation({
    mutationFn: () =>
      api.updateComplianceCycle(organizationId, cycle.id, {
        name: name.trim() || undefined,
        status: status || undefined,
      }),
    onSuccess: () => {
      setEditing(false);
      onError(null);
      onChanged();
    },
    onError: (e) => onError(e instanceof ApiError ? e.message : "Update cycle failed"),
  });

  const remove = useMutation({
    mutationFn: () => api.deleteComplianceCycle(organizationId, cycle.id),
    onSuccess: () => {
      onError(null);
      onChanged();
    },
    onError: (e) => onError(e instanceof ApiError ? e.message : "Delete cycle failed"),
  });

  return (
    <li className="rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-800">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium">{cycle.name}</span>
        <div className="flex items-center gap-2">
          <span className="rounded bg-slate-100 px-2 py-0.5 text-xs uppercase dark:bg-slate-800">
            {cycle.status}
          </span>
          <button
            type="button"
            className="text-xs text-slate-600 hover:underline dark:text-slate-400"
            onClick={() => setShowStatus((v) => !v)}
          >
            {showStatus ? "Hide status" : "Status"}
          </button>
          {canManage && !editing && (
            <>
              <button
                type="button"
                className="text-xs text-emerald-700 hover:underline dark:text-emerald-300"
                onClick={() => {
                  setName(cycle.name);
                  setStatus(cycle.status);
                  setEditing(true);
                }}
              >
                Edit
              </button>
              <button
                type="button"
                className="text-xs text-red-600 hover:underline dark:text-red-400"
                disabled={remove.isPending}
                onClick={() => {
                  if (window.confirm(`Delete cycle "${cycle.name}"?`)) remove.mutate();
                }}
              >
                Delete
              </button>
            </>
          )}
        </div>
      </div>

      {(cycle.starts_at || cycle.ends_at) && !editing && (
        <p className="mt-1 text-xs text-slate-500">
          {cycle.starts_at ?? "—"} → {cycle.ends_at ?? "—"}
        </p>
      )}

      {editing && (
        <div className="mt-2 grid gap-2 md:grid-cols-2">
          <label className="text-xs">
            Name
            <input
              className="mt-1 w-full min-h-9 rounded border border-slate-300 bg-slate-50 px-2 text-sm dark:border-slate-700 dark:bg-slate-800"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="text-xs">
            Status
            <select
              className="mt-1 w-full min-h-9 rounded border border-slate-300 bg-slate-50 px-2 text-sm dark:border-slate-700 dark:bg-slate-800"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="planned">planned</option>
              <option value="active">active</option>
              <option value="closed">closed</option>
            </select>
          </label>
          <div className="md:col-span-2 flex gap-2">
            <button
              type="button"
              className="min-h-9 rounded bg-emerald-600 px-3 text-xs font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
              disabled={update.isPending}
              onClick={() => update.mutate()}
            >
              {update.isPending ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              className="min-h-9 rounded border border-slate-300 px-3 text-xs dark:border-slate-700"
              onClick={() => setEditing(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {showStatus && (
        <div className="mt-3 rounded border border-slate-200 bg-slate-50 p-2 text-xs dark:border-slate-800 dark:bg-slate-950/20">
          {cycleStatus.isLoading && <p className="text-slate-500">Loading cycle status…</p>}
          {cycleStatus.error && <p className="text-red-600">Failed to load cycle status</p>}
          {cycleStatus.data && (
            <div className="grid gap-2 sm:grid-cols-2">
              <div>
                <p className="font-medium text-slate-700 dark:text-slate-300">Evidence coverage</p>
                <p className="mt-1 text-slate-600 dark:text-slate-400">
                  Controls: {cycleStatus.data.controls_with_any_evidence}/{cycleStatus.data.controls_total} with evidence
                </p>
                <p className="mt-1 text-slate-600 dark:text-slate-400">
                  Missing (design/impl/operating):{" "}
                  {cycleStatus.data.missing_evidence_controls_by_category.design ?? 0}/
                  {cycleStatus.data.missing_evidence_controls_by_category.implementation ?? 0}/
                  {cycleStatus.data.missing_evidence_controls_by_category.operating ?? 0}
                </p>
              </div>
              <div>
                <p className="font-medium text-slate-700 dark:text-slate-300">Check expiry (org)</p>
                <p className="mt-1 text-slate-600 dark:text-slate-400">
                  Active: {cycleStatus.data.checks_active} · Expiring soon: {cycleStatus.data.checks_expiring_soon} ·
                  Expired: {cycleStatus.data.checks_expired}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </li>
  );
}

function ControlEvidencePanel({
  organizationId,
  controlId,
  canManage,
}: {
  organizationId: string;
  controlId: string;
  canManage: boolean;
}) {
  const qc = useQueryClient();
  const [uploadErr, setUploadErr] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("implementation");
  const [downloadErr, setDownloadErr] = useState<string | null>(null);
  const [deleteErr, setDeleteErr] = useState<string | null>(null);
  const [supersedeTargetId, setSupersedeTargetId] = useState<string | null>(null);

  const evidence = useQuery({
    queryKey: ["grc-evidence", organizationId, controlId],
    queryFn: () => api.listControlEvidence(organizationId, controlId),
    enabled: !!organizationId && !!controlId,
  });

  const upload = useMutation({
    mutationFn: () =>
      api.uploadControlEvidence(organizationId, controlId, {
        file: file!,
        category,
        title: title.trim() || file!.name,
        supersedes_evidence_id: supersedeTargetId,
      }),
    onSuccess: () => {
      setUploadErr(null);
      setFile(null);
      setTitle("");
      setSupersedeTargetId(null);
      void qc.invalidateQueries({ queryKey: ["grc-evidence", organizationId, controlId] });
    },
    onError: (e) => setUploadErr(e instanceof ApiError ? e.message : "Evidence upload failed"),
  });

  const download = useMutation({
    mutationFn: async (evidenceId: string) => api.downloadEvidence(organizationId, evidenceId),
    onSuccess: ({ blob, filename }) => {
      setDownloadErr(null);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename ?? "evidence.bin";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    },
    onError: (e) => setDownloadErr(e instanceof ApiError ? e.message : "Evidence download failed"),
  });

  const remove = useMutation({
    mutationFn: async (evidenceId: string) => api.deleteEvidence(organizationId, evidenceId),
    onSuccess: () => {
      setDeleteErr(null);
      void qc.invalidateQueries({ queryKey: ["grc-evidence", organizationId, controlId] });
    },
    onError: (e) => setDeleteErr(e instanceof ApiError ? e.message : "Evidence delete failed"),
  });

  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50/60 p-3 dark:border-slate-800 dark:bg-slate-950/20">
      <p className="text-xs font-medium text-slate-700 dark:text-slate-300">Evidence</p>
      {evidence.isLoading && <p className="mt-1 text-xs text-slate-500">Loading…</p>}
      <ul className="mt-2 space-y-1 text-xs">
        {(evidence.data ?? []).slice(0, 5).map((ev) => (
          <li key={ev.id} className="flex items-center justify-between gap-2">
            <div className="flex min-w-0 flex-1 items-center gap-2">
              <button
                type="button"
                className="min-w-0 flex-1 truncate text-left text-emerald-700 hover:underline dark:text-emerald-300"
                onClick={() => download.mutate(ev.id)}
                disabled={download.isPending}
                title="Download evidence"
              >
                {ev.title}
              </button>
              <span className="shrink-0 rounded bg-slate-100 px-2 py-0.5 text-[10px] uppercase dark:bg-slate-800">
                {ev.category}
              </span>
            </div>
            {canManage && (
              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  className="text-[10px] text-slate-600 hover:underline dark:text-slate-400"
                  onClick={() => setSupersedeTargetId(ev.id)}
                  title="Upload a new version that supersedes this evidence"
                >
                  Replace
                </button>
                <button
                  type="button"
                  className="text-[10px] text-red-600 hover:underline dark:text-red-400"
                  disabled={remove.isPending}
                  onClick={() => {
                    if (window.confirm(`Delete evidence "${ev.title}"?`)) remove.mutate(ev.id);
                  }}
                  title="Delete evidence"
                >
                  Delete
                </button>
              </div>
            )}
          </li>
        ))}
        {!evidence.data?.length && <li className="text-xs text-slate-500">No evidence uploaded.</li>}
      </ul>
      {downloadErr && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{downloadErr}</p>}
      {deleteErr && <p className="mt-2 text-xs text-red-600 dark:text-red-400">{deleteErr}</p>}

      {canManage && (
        <div className="mt-3 space-y-2">
          {supersedeTargetId && (
            <div className="rounded border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200">
              Replacing evidence. The next upload will supersede{" "}
              <span className="font-mono">{supersedeTargetId}</span>.{" "}
              <button
                type="button"
                className="underline"
                onClick={() => setSupersedeTargetId(null)}
              >
                Cancel
              </button>
            </div>
          )}
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <input
              type="file"
              className="text-xs"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
            <select
              className="min-h-9 rounded border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-800"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="design">design</option>
              <option value="implementation">implementation</option>
              <option value="operating">operating</option>
            </select>
          </div>
          <input
            className="min-h-9 w-full rounded border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-800"
            placeholder="Evidence title (optional)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <button
            type="button"
            disabled={!file || upload.isPending}
            onClick={() => upload.mutate()}
            className="min-h-9 rounded bg-emerald-600 px-3 text-xs font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            {supersedeTargetId ? "Upload replacement" : "Upload"}
          </button>
          {uploadErr && <p className="text-xs text-red-600 dark:text-red-400">{uploadErr}</p>}
        </div>
      )}
    </div>
  );
}

