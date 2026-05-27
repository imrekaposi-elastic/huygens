import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import {
  ComplianceMembershipLegend,
  MembershipCheckbox,
} from "@/components/compliance/ComplianceMembershipLegend";

type Props = {
  organizationId: string;
  projectId: string;
  agentId: string;
  vmName: string;
  open: boolean;
  onClose: () => void;
};

export function PlacementRationaleDialog({
  organizationId,
  projectId,
  agentId,
  vmName,
  open,
  onClose,
}: Props) {
  const rationale = useQuery({
    queryKey: ["placement-rationale", organizationId, projectId, agentId, vmName],
    queryFn: () =>
      api.placementRationale(organizationId, {
        resource_type: "vm",
        project_id: projectId,
        agent_id: agentId,
        name: vmName,
      }),
    enabled: open && !!organizationId,
  });

  if (!open) return null;

  const body = rationale.data;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal
      aria-labelledby="placement-rationale-title"
    >
      <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-900">
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 id="placement-rationale-title" className="text-lg font-medium">
            Why is {vmName} here?
          </h2>
          <button
            type="button"
            className="text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        {rationale.isLoading && <p className="text-sm text-slate-500">Loading…</p>}
        {rationale.isError && (
          <p className="text-sm text-red-600 dark:text-red-400">Could not load placement rationale.</p>
        )}
        {body && (
          <div className="space-y-4 text-sm">
            <p className="text-slate-600 dark:text-slate-400">
              Project <strong>{body.project_name ?? body.project_id}</strong>
              {body.agent_name && (
                <>
                  {" "}
                  · Agent <strong>{body.agent_name}</strong>
                </>
              )}
            </p>
            {body.inherited_traits.length > 0 && (
              <section>
                <h3 className="mb-1 font-medium text-slate-700 dark:text-slate-300">Inherited traits</h3>
                <ul className="list-inside list-disc space-y-1 text-slate-600 dark:text-slate-400">
                  {body.inherited_traits.map((t) => (
                    <li key={`${t.scope}-${t.trait_key}`}>
                      [{t.scope}] {t.title}
                      {t.region_name && ` (${t.region_name})`}
                      <span className="ml-1 text-xs uppercase">{t.moscow}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
            <ComplianceMembershipLegend className="mb-2" compact />
            {(body.inherited_compliance_items?.length ?? 0) > 0 && (
              <section>
                <h3 className="mb-1 font-medium text-slate-700 dark:text-slate-300">
                  Inherited membership
                </h3>
                <ul className="space-y-1">
                  {body.inherited_compliance_items!.map((i) => (
                    <li key={`inherited-${i.id}`} className="flex items-center gap-2 text-sm">
                      <MembershipCheckbox variant="inherited" />
                      <span>{i.name}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {body.compliance_items.length > 0 && (
              <section>
                <h3 className="mb-1 font-medium text-slate-700 dark:text-slate-300">
                  Direct membership
                </h3>
                <ul className="space-y-1">
                  {body.compliance_items.map((i) => (
                    <li key={i.id} className="flex items-center gap-2 text-sm">
                      <MembershipCheckbox variant="direct" />
                      <span>{i.name}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {body.placement_note && (
              <p className="rounded border border-slate-200 bg-slate-50 p-2 dark:border-slate-700 dark:bg-slate-800">
                {body.placement_note}
              </p>
            )}
            {body.config_drift != null && (
              <p>
                Config drift:{" "}
                <span className={body.config_drift ? "text-amber-600" : "text-emerald-600"}>
                  {body.config_drift ? "detected" : "none"}
                </span>
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
