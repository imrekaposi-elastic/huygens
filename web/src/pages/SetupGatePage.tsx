import { useEffect } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { needsPlatformSetup } from "@/auth/setup";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import { PlatformSetupPage } from "@/pages/PlatformSetupPage";

/** Only platform admins with zero organizations may access /setup. */
export function SetupGatePage() {
  const { loading, organizations } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (loading) return;
    if (!getAccessToken()) {
      void navigate({ to: "/login", replace: true });
      return;
    }
    if (!isPlatformAdmin(getAccessToken())) {
      void navigate({ to: "/", replace: true });
      return;
    }
    if (!needsPlatformSetup(organizations)) {
      void navigate({ to: "/", replace: true });
    }
  }, [loading, organizations, navigate]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        Loading…
      </div>
    );
  }

  if (!needsPlatformSetup(organizations)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        Loading…
      </div>
    );
  }

  return <PlatformSetupPage />;
}
