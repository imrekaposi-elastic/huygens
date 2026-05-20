import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import { CogIcon } from "@/components/icons/NavIcons";
import { CloudInitDialog, type CloudInitProfile } from "@/pages/project/CloudInitDialog";
import { useProjectWorkspace } from "@/pages/project/projectContext";
import { ResourceList, ResourceListEmpty, ResourceListItem } from "@/pages/project/ResourceList";

type Props = { projectId: string };

function toProfile(row: Record<string, unknown>): CloudInitProfile {
  return {
    name: String(row.name ?? ""),
    user_data: String(row.user_data ?? ""),
    meta_data: String(row.meta_data ?? ""),
    network_config: row.network_config != null ? String(row.network_config) : null,
    ssh_keys: Array.isArray(row.ssh_keys) ? (row.ssh_keys as string[]) : [],
  };
}

export function ProjectCloudInitTab({ projectId }: Props) {
  const { agentId } = useProjectWorkspace();
  const qc = useQueryClient();
  const [dialog, setDialog] = useState<"create" | { edit: CloudInitProfile } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["cloud-init", projectId, agentId],
    queryFn: () => api.listCloudInitProfiles(projectId, agentId),
    enabled: !!agentId,
  });

  const remove = useMutation({
    mutationFn: (name: string) => api.deleteCloudInitProfile(projectId, agentId, name),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["cloud-init", projectId, agentId] }),
  });

  if (!agentId) {
    return <p className="text-slate-500 dark:text-slate-500">Select an agent in the project header to manage cloud-init.</p>;
  }

  const profiles = (data ?? []).map((r) => toProfile(r as Record<string, unknown>));

  return (
    <>
      <ResourceList
        title="Cloud-init profiles"
        titleIcon={<CogIcon />}
        description="Reusable user-data, meta-data, and network-config templates on the agent."
        onNew={() => setDialog("create")}
        loading={isLoading}
      >
        {profiles.length === 0 && !isLoading ? (
          <ResourceListEmpty message="No cloud-init profiles. Click New to create one." />
        ) : (
          profiles.map((p) => (
            <ResourceListItem
              key={p.name}
              name={p.name}
              subtitle={p.network_config ? "Includes network-config" : "user-data + meta-data"}
              onEdit={() => setDialog({ edit: p })}
              onDelete={() => {
                if (window.confirm(`Delete cloud-init profile "${p.name}"?`)) remove.mutate(p.name);
              }}
            />
          ))
        )}
      </ResourceList>

      <CloudInitDialog
        open={dialog !== null}
        mode={dialog === "create" ? "create" : "edit"}
        projectId={projectId}
        agentId={agentId}
        initial={dialog && dialog !== "create" ? dialog.edit : null}
        onClose={() => setDialog(null)}
        onSaved={() => void qc.invalidateQueries({ queryKey: ["cloud-init", projectId, agentId] })}
      />
      {remove.isError && (
        <p className="text-sm text-red-700 dark:text-red-300">
          {remove.error instanceof ApiError ? remove.error.message : "Delete failed"}
        </p>
      )}
    </>
  );
}
