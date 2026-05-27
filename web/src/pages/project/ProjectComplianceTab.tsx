import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { canAccessCompliance, canAssignComplianceCriticality } from "@/auth/permissions";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import { api } from "@/api/client";
import { AssetCriticalityEditor } from "@/components/compliance/AssetCriticalityEditor";
import { CheckmarkIcon } from "@/components/icons/NavIcons";

type Props = { projectId: string };

export function ProjectComplianceTab({ projectId }: Props) {
  const { user, selectedOrgId } = useAuth();
  const platformAdmin = isPlatformAdmin(getAccessToken());
  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });
  const organizationId = project.data?.organization_id ?? selectedOrgId ?? "";
  const canAccess = canAccessCompliance(user, organizationId, platformAdmin);
  const canEdit = canAssignComplianceCriticality(user, organizationId, platformAdmin);

  if (!canAccess) {
    return (
      <p className="text-sm text-slate-600 dark:text-slate-400">
        You need a compliance org role to view assignments.{" "}
        <Link to="/compliance/overview" className="text-emerald-600 hover:underline dark:text-emerald-400">
          Org compliance
        </Link>
      </p>
    );
  }

  if (!organizationId) {
    return <p className="text-sm text-slate-500">Loading organization…</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="flex items-center gap-2 text-lg font-medium">
          <CheckmarkIcon className="size-5 text-emerald-600/90 dark:text-emerald-400/90" />
          Asset criticality
        </h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Link org catalog standards directly to this project (green). A standard also appears in
          blue when <strong>every</strong> VM and network in the project satisfies it (directly or
          via provider/region inheritance). Use <strong>Compliance</strong> on the Virtual machines
          or Networks tab to assign per workload.
        </p>
      </div>
      <AssetCriticalityEditor
        organizationId={organizationId}
        title="Project-wide standards"
        canEdit={canEdit}
        queryKey={["project-criticality", organizationId, projectId]}
        load={() => api.getProjectCriticality(organizationId, projectId)}
        save={(body) => api.setProjectCriticality(organizationId, projectId, body)}
      />
    </div>
  );
}
