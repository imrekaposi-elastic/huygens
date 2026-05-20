import { Link } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { canAccessIpam } from "@/auth/permissions";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import { IpamPage } from "@/pages/ipam/IpamPage";

export function IpamGatePage() {
  const { user, selectedOrgId } = useAuth();
  const platformAdmin = isPlatformAdmin(getAccessToken());

  if (!canAccessIpam(user, selectedOrgId, platformAdmin)) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-6">
        <p className="text-slate-600 dark:text-slate-400">
          Organization administrators manage IP address pools and project subnet assignments.{" "}
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

  return <IpamPage organizationId={selectedOrgId} />;
}
