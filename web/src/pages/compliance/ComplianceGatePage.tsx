import { Link } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { canAccessCompliance } from "@/auth/permissions";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import { ComplianceLayout } from "@/pages/compliance/ComplianceLayout";

export function ComplianceGatePage() {
  const { user, selectedOrgId } = useAuth();
  const platformAdmin = isPlatformAdmin(getAccessToken());

  if (!canAccessCompliance(user, selectedOrgId, platformAdmin)) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-6">
        <p className="text-slate-600 dark:text-slate-400">
          Compliance views require an organization compliance or admin role.{" "}
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

  return <ComplianceLayout organizationId={selectedOrgId} />;
}
