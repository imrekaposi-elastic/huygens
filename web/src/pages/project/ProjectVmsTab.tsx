import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { VmIcon } from "@/components/icons/NavIcons";
import { liveQueryOptions } from "@/lib/liveRefresh";
import { useProjectWorkspace } from "@/pages/project/projectContext";
import { VmDialog } from "@/pages/project/VmDialog";
import { VmListTable, type VmRow } from "@/pages/project/VmListTable";

type Props = { projectId: string };

export function ProjectVmsTab({ projectId }: Props) {
  const { agentId } = useProjectWorkspace();
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<"create" | { edit: Record<string, unknown> } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["vms", projectId, agentId],
    queryFn: () => api.listVms(projectId, agentId),
    enabled: !!agentId,
    ...liveQueryOptions,
  });

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ["vms", projectId, agentId] });
    void qc.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const remove = useMutation({
    mutationFn: (name: string) => api.deleteVm(projectId, agentId, name),
    onSuccess: invalidate,
  });

  const unassign = useMutation({
    mutationFn: (name: string) => api.unassignResourceFromProject(projectId, agentId, "vm", name),
    onSuccess: invalidate,
  });

  if (!agentId) {
    return <p className="text-slate-500 dark:text-slate-500">Select an agent in the project header to manage VMs.</p>;
  }

  const vms = (data ?? []) as VmRow[];

  return (
    <>
      <div className="space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-lg font-medium">
              <span className="inline-flex h-5 w-5 shrink-0 text-emerald-600/90 dark:text-emerald-400/90">
                <VmIcon />
              </span>
              Virtual machines
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-500">
              Power is hypervisor state (libvirt). SSH checkbox is a read-only guest probe on port 22.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setDialog("create")}
            className="min-h-10 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500"
          >
            New
          </button>
        </div>
        <VmListTable
          vms={vms}
          loading={isLoading}
          emptyMessage="No VMs listed for this agent."
          actions={(vm) => {
            const name = String(vm.name ?? "");
            return (
              <div className="flex flex-col items-end gap-1">
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setDialog({ edit: vm as Record<string, unknown> })}
                    className="rounded border border-slate-300 dark:border-slate-600 px-3 py-1.5 text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:bg-slate-800"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (window.confirm(`Delete VM "${name}" on the hypervisor?`)) remove.mutate(name);
                    }}
                    className="rounded border border-red-300 dark:border-red-900/80 px-3 py-1.5 text-sm text-red-700 dark:text-red-300 hover:bg-red-50 dark:bg-red-950/40"
                  >
                    Delete
                  </button>
                </div>
                <button
                  type="button"
                  className="text-xs text-slate-600 dark:text-slate-400 underline"
                  onClick={() => unassign.mutate(name)}
                >
                  Unassign from project
                </button>
              </div>
            );
          }}
        />
      </div>

      <VmDialog
        open={dialog !== null}
        mode={dialog === "create" ? "create" : "edit"}
        projectId={projectId}
        agentId={agentId}
        initial={dialog && dialog !== "create" ? dialog.edit : null}
        onClose={() => setDialog(null)}
        onSaved={invalidate}
      />
    </>
  );
}
