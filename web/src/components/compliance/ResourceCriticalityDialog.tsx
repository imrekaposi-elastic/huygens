import { useAuth } from "@/auth/AuthContext";
import { canAssignComplianceCriticality } from "@/auth/permissions";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import { api } from "@/api/client";
import { AssetCriticalityEditor } from "@/components/compliance/AssetCriticalityEditor";

type Props = {
  open: boolean;
  onClose: () => void;
  organizationId: string;
  projectId: string;
  agentId: string;
  resourceType: "vm" | "network";
  resourceName: string;
};

export function ResourceCriticalityDialog({
  open,
  onClose,
  organizationId,
  projectId,
  agentId,
  resourceType,
  resourceName,
}: Props) {
  const { user } = useAuth();
  const platformAdmin = isPlatformAdmin(getAccessToken());
  const canEdit = canAssignComplianceCriticality(user, organizationId, platformAdmin);

  if (!open) return null;

  const label = resourceType === "vm" ? "VM" : "network";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal
    >
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl border border-slate-200 bg-white p-5 shadow-xl dark:border-slate-700 dark:bg-slate-900">
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 className="text-lg font-medium">
            Compliance — {label} {resourceName}
          </h2>
          <button
            type="button"
            className="text-sm text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        <AssetCriticalityEditor
          organizationId={organizationId}
          title="Linked catalog standards"
          description={`Select org compliance items assigned directly to this ${label}. Standards from a compliant provider or region are inherited automatically.`}
          canEdit={canEdit}
          queryKey={[
            "resource-criticality",
            organizationId,
            projectId,
            agentId,
            resourceType,
            resourceName,
          ]}
          load={() =>
            api.getResourceCriticality(organizationId, projectId, resourceType, resourceName, agentId)
          }
          save={(body) =>
            api.setResourceCriticality(
              organizationId,
              projectId,
              resourceType,
              resourceName,
              agentId,
              body,
            )
          }
          onSaveSuccess={onClose}
        />
      </div>
    </div>
  );
}
