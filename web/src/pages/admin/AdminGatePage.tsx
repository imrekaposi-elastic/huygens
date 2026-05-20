import { Link } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { canAccessAdmin } from "@/auth/permissions";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import { AdminLayout } from "@/pages/admin/AdminLayout";

export function AdminGatePage() {
  const { user, selectedOrgId } = useAuth();
  const platformAdmin = isPlatformAdmin(getAccessToken());

  if (!canAccessAdmin(user, selectedOrgId, platformAdmin)) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-6">
        <p className="text-slate-600 dark:text-slate-400">
          Organization administrators can manage users, IdP mappings, and roles here.{" "}
          <Link to="/" className="text-emerald-600 dark:text-emerald-400 hover:underline">
            Back to home
          </Link>
        </p>
      </div>
    );
  }

  return <AdminLayout platformAdmin={platformAdmin} />;
}
