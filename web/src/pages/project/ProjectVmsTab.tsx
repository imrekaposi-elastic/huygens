import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useProjectWorkspace } from "@/pages/project/projectContext";
import { ResourceList, ResourceListEmpty, ResourceListItem } from "@/pages/project/ResourceList";
import { VmDialog } from "@/pages/project/VmDialog";
import { formatVmStatusLine, guestStatusHint } from "@/lib/vmStatus";

type Props = { projectId: string };

export function ProjectVmsTab({ projectId }: Props) {
  const { agentId } = useProjectWorkspace();
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<"create" | { edit: Record<string, unknown> } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["vms", projectId, agentId],
    queryFn: () => api.listVms(projectId, agentId),
    enabled: !!agentId,
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
    return <p className="text-slate-500">Select an agent in the project header to manage VMs.</p>;
  }

  const vms = data ?? [];

  return (
    <>
      <ResourceList
        title="Virtual machines"
        description="Create on the agent or assign orphaned VMs from the inventory dashboard."
        onNew={() => setDialog("create")}
        loading={isLoading}
      >
        {vms.length === 0 && !isLoading ? (
          <ResourceListEmpty message="No VMs listed for this agent." />
        ) : (
          vms.map((vm) => {
            const name = String(vm.name ?? "");
            const subtitle = formatVmStatusLine({
              libvirt_state: String(vm.libvirt_state ?? ""),
              guest_status: String(vm.status ?? ""),
              memory_mib: typeof vm.memory_mib === "number" ? vm.memory_mib : null,
            });
            const hint = guestStatusHint(String(vm.status ?? ""));
            return (
              <ResourceListItem
                key={name}
                name={name}
                subtitle={subtitle || undefined}
                onEdit={() => setDialog({ edit: vm })}
                onDelete={() => {
                  if (window.confirm(`Delete VM "${name}" on the hypervisor?`)) remove.mutate(name);
                }}
                deleteLabel="Delete on agent"
                extra={
                  <>
                    {hint && <p className="text-xs text-amber-400/90">{hint}</p>}
                    <button
                      type="button"
                      className="mt-1 block text-xs text-slate-400 underline"
                      onClick={() => unassign.mutate(name)}
                    >
                      Unassign from project
                    </button>
                  </>
                }
              />
            );
          })
        )}
      </ResourceList>

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
