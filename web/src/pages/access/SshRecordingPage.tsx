import { Link, useParams } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { downloadSshRecording } from "@/api/client";
import { SshRecordingPlayer } from "@/components/ssh/SshRecordingPlayer";

export function SshRecordingPage() {
  const { sessionId } = useParams({ strict: false }) as { sessionId: string };
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let objectUrl: string | null = null;
    setLoading(true);
    setError(null);

    downloadSshRecording(sessionId)
      .then(({ blob }) => {
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [sessionId]);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
          Session replay
        </h1>
        <Link
          to="/access"
          className="text-sm text-emerald-600 hover:underline dark:text-emerald-400"
        >
          ← Sessions
        </Link>
      </div>
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Session <code className="text-xs">{sessionId}</code> — asciicast v2 recording.
      </p>
      {loading && <p className="text-sm text-slate-500">Loading recording…</p>}
      {error && (
        <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {error}
        </p>
      )}
      {src && !error ? <SshRecordingPlayer src={src} /> : null}
    </div>
  );
}
