import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { ProjectAccessPanel } from "@/components/ProjectAccessPanel";
import { canManageOrgUsers } from "@/auth/permissions";
import { useAuth } from "@/auth/AuthContext";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import { Link } from "@tanstack/react-router";

type Props = { projectId: string };

export function ProjectAccessTab({ projectId }: Props) {
  const { user, selectedOrgId } = useAuth();
  const platformAdmin = isPlatformAdmin(getAccessToken());
  const canManage = canManageOrgUsers(user, selectedOrgId, platformAdmin);

  const project = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId),
  });

  if (!canManage) {
    return (
      <p className="text-slate-600 dark:text-slate-400">
        Project access is managed by organization or project administrators.{" "}
        <Link to="/admin/users" className="text-emerald-600 dark:text-emerald-400 hover:underline">
          Open Admin
        </Link>
      </p>
    );
  }

  return (
    <ProjectAccessPanel
      projectId={projectId}
      projectName={project.data?.name}
    />
  );
}
