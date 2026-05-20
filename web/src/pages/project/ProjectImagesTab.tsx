import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import { CdIcon } from "@/components/icons/NavIcons";
import { ImageDialog } from "@/pages/project/ImageDialog";
import { useProjectWorkspace } from "@/pages/project/projectContext";
import { ResourceList, ResourceListEmpty, ResourceListItem } from "@/pages/project/ResourceList";

type ImageRow = {
  name: string;
  status: string;
  source: string;
  source_type: string;
  size_bytes: number | null;
  error: string | null;
};

function toImage(row: Record<string, unknown>): ImageRow {
  return {
    name: String(row.name ?? ""),
    status: String(row.status ?? "unknown"),
    source: String(row.source ?? ""),
    source_type: String(row.source_type ?? ""),
    size_bytes: typeof row.size_bytes === "number" ? row.size_bytes : null,
    error: row.error != null ? String(row.error) : null,
  };
}

function formatBytes(n: number | null): string {
  if (n == null) return "—";
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

function statusClass(status: string): string {
  if (status === "ready") return "text-emerald-600 dark:text-emerald-400";
  if (status === "error") return "text-red-600 dark:text-red-400";
  return "text-amber-700 dark:text-amber-400";
}

type Props = { projectId: string };

export function ProjectImagesTab({ projectId }: Props) {
  const { agentId } = useProjectWorkspace();
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["images", projectId, agentId],
    queryFn: () => api.listImages(projectId, agentId),
    enabled: !!agentId,
  });

  const remove = useMutation({
    mutationFn: (name: string) => api.deleteImage(projectId, agentId, name),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["images", projectId, agentId] }),
  });

  if (!agentId) {
    return <p className="text-slate-500 dark:text-slate-500">Select an agent in the project header to manage images.</p>;
  }

  const images = (data ?? []).map((r) => toImage(r as Record<string, unknown>));

  return (
    <>
      <ResourceList
        title="Images"
        titleIcon={
          <span className="inline-flex h-5 w-5 shrink-0 text-emerald-600/90 dark:text-emerald-400/90">
            <CdIcon />
          </span>
        }
        description="Managed base disks on the agent. Use with a cloud-init profile when creating VMs."
        onNew={() => setCreateOpen(true)}
        newLabel="Register image"
        loading={isLoading}
      >
        {images.length === 0 && !isLoading ? (
          <ResourceListEmpty message="No images registered. Add a base disk image to use with cloud-init." />
        ) : (
          images.map((img) => (
            <ResourceListItem
              key={img.name}
              name={img.name}
              subtitle={`${img.source_type} · ${formatBytes(img.size_bytes)}`}
              deleteLabel="Delete"
              onDelete={() => {
                if (window.confirm(`Delete image "${img.name}" from the agent registry?`)) {
                  remove.mutate(img.name);
                }
              }}
              extra={
                <div className="mt-1 space-y-0.5 text-xs">
                  <p>
                    Status:{" "}
                    <span className={`font-mono ${statusClass(img.status)}`}>{img.status}</span>
                  </p>
                  <p className="truncate font-mono text-slate-500 dark:text-slate-500" title={img.source}>
                    {img.source}
                  </p>
                  {img.error && <p className="text-red-600 dark:text-red-400">{img.error}</p>}
                </div>
              }
            />
          ))
        )}
      </ResourceList>

      <ImageDialog
        open={createOpen}
        projectId={projectId}
        agentId={agentId}
        onClose={() => setCreateOpen(false)}
        onSaved={() => void qc.invalidateQueries({ queryKey: ["images", projectId, agentId] })}
      />
      {remove.isError && (
        <p className="text-sm text-red-700 dark:text-red-300">
          {remove.error instanceof ApiError ? remove.error.message : "Delete failed"}
        </p>
      )}
    </>
  );
}
