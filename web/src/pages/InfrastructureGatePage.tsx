import { Link } from "@tanstack/react-router";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import { InfrastructureProvidersPage } from "@/pages/InfrastructureProvidersPage";

export function InfrastructureGatePage() {
  if (!isPlatformAdmin(getAccessToken())) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-6">
        <p className="text-slate-600 dark:text-slate-400">
          Infrastructure providers are managed by platform administrators.{" "}
          <Link to="/" className="text-emerald-600 dark:text-emerald-400 hover:underline">
            Back to dashboard
          </Link>
        </p>
      </div>
    );
  }
  return <InfrastructureProvidersPage />;
}
