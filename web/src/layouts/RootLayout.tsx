import { useEffect } from "react";
import { Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { needsPlatformSetup } from "@/auth/setup";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import { NoOrganizationAccess } from "@/components/NoOrganizationAccess";

const PUBLIC_PATHS = new Set(["/login", "/auth/callback"]);

function LoadingScreen({ message = "Loading…" }: { message?: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 dark:bg-slate-950 text-slate-600 dark:text-slate-400">
      {message}
    </div>
  );
}

export function RootLayout() {
  const { loading, organizations } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const hasToken = !!getAccessToken();

  useEffect(() => {
    if (loading || !hasToken) return;
    if (PUBLIC_PATHS.has(pathname) || pathname === "/setup") return;
    if (needsPlatformSetup(organizations)) {
      void navigate({ to: "/setup", replace: true });
    }
  }, [loading, hasToken, organizations, pathname, navigate]);

  if (loading && hasToken && !PUBLIC_PATHS.has(pathname)) {
    return <LoadingScreen />;
  }

  if (
    !loading &&
    hasToken &&
    pathname !== "/setup" &&
    needsPlatformSetup(organizations)
  ) {
    return <LoadingScreen message="Starting setup…" />;
  }

  if (
    !loading &&
    hasToken &&
    !PUBLIC_PATHS.has(pathname) &&
    pathname !== "/setup" &&
    organizations.length === 0 &&
    !isPlatformAdmin(getAccessToken())
  ) {
    return <NoOrganizationAccess />;
  }

  return <Outlet />;
}
