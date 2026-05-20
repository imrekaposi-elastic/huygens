import { useEffect, useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { parseTokenFromHash, setAccessToken } from "@/auth/token";
import { useAuth } from "@/auth/AuthContext";

export function OidcCallbackPage() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (window.location.search.match(/(token|access_token)=/)) {
      setError("JWT must not be in query string. Use IAM OIDC redirect with URL fragment.");
      return;
    }
    const token = parseTokenFromHash(window.location.hash);
    if (!token) {
      setError("Missing #access_token in callback URL");
      return;
    }
    setAccessToken(token);
    window.history.replaceState(null, "", window.location.pathname);
    refresh()
      .then(() => navigate({ to: "/" }))
      .catch(() => setError("Failed to load user profile"));
  }, [navigate, refresh]);

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <p className="text-slate-400">{error ?? "Completing sign-in…"}</p>
    </div>
  );
}
