import { Link } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { canAccessTopology } from "@/auth/permissions";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import { TopologyPage } from "@/pages/topology/TopologyPage";

export function TopologyGatePage() {
  const { user, selectedOrgId } = useAuth();
  const platformAdmin = isPlatformAdmin(getAccessToken());

  if (!canAccessTopology(user, selectedOrgId, platformAdmin)) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-6">
        <p className="text-slate-600 dark:text-slate-400">
          Select an organization you belong to, or ask an administrator for access.{" "}
          <Link to="/" className="text-emerald-600 dark:text-emerald-400 hover:underline">
            Back to home
          </Link>
        </p>
      </div>
    );
  }

  if (!selectedOrgId) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-6">
        <p className="text-slate-600 dark:text-slate-400">Select an organization in the header.</p>
      </div>
    );
  }

  return <TopologyPage organizationId={selectedOrgId} />;
}
