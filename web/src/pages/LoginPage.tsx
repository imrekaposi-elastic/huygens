import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { ApiError } from "@/api/client";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("platform-admin");
  const [password, setPassword] = useState("platform-admin-dev");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username, password);
      void navigate({ to: "/" });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-sm rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-lg"
      >
        <h1 className="text-xl font-semibold text-emerald-400">Huygens Console</h1>
        <p className="mt-1 text-sm text-slate-400">Sign in with local credentials</p>
        {error && (
          <p className="mt-3 rounded bg-red-950/50 px-3 py-2 text-sm text-red-300">{error}</p>
        )}
        <label className="mt-4 block text-sm">
          Username
          <input
            className="mt-1 w-full min-h-11 rounded border border-slate-700 bg-slate-800 px-3"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />
        </label>
        <label className="mt-3 block text-sm">
          Password
          <input
            type="password"
            className="mt-1 w-full min-h-11 rounded border border-slate-700 bg-slate-800 px-3"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="mt-6 w-full min-h-11 rounded-lg bg-emerald-600 font-medium hover:bg-emerald-500 disabled:opacity-50"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
