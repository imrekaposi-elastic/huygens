import { Link, useNavigate, useParams } from "@tanstack/react-router";
import { useState } from "react";
import { SshTerminal } from "@/components/ssh/SshTerminal";

export function SshTerminalPage() {
  const { sessionId } = useParams({ strict: false }) as { sessionId: string };
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
          SSH terminal
        </h1>
        <Link
          to="/access"
          className="text-sm text-emerald-600 hover:underline dark:text-emerald-400"
        >
          ← Sessions
        </Link>
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Session <code className="text-xs">{sessionId}</code> — all input is recorded.
      </p>
      {error && (
        <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {error}
        </p>
      )}
      <SshTerminal
        sessionId={sessionId}
        onError={setError}
        onClose={() => {
          void navigate({ to: "/access" });
        }}
      />
    </div>
  );
}
