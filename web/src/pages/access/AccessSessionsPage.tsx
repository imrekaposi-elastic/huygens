import { useCallback, useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { canConnectSsh } from "@/auth/permissions";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import {
  deleteSshSession,
  downloadSshRecording,
  listSshSessions,
  type SshSession,
} from "@/api/client";

export function AccessSessionsPage() {
  const { user, selectedOrgId } = useAuth();
  const platformAdmin = isPlatformAdmin(getAccessToken());
  const showConnect = canConnectSsh(user, selectedOrgId, platformAdmin);
  const [sessions, setSessions] = useState<SshSession[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const reload = useCallback(() => {
    if (!selectedOrgId) return;
    listSshSessions(selectedOrgId)
      .then(setSessions)
      .catch((e: Error) => setError(e.message));
  }, [selectedOrgId]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function handleDownload(sessionId: string) {
    setDownloadError(null);
    setDownloadingId(sessionId);
    try {
      const { blob, filename } = await downloadSshRecording(sessionId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setDownloadingId(null);
    }
  }

  async function handleDelete(sessionId: string, vmName: string) {
    if (!window.confirm(`Delete SSH session for ${vmName}? Recording will be removed.`)) return;
    setDownloadError(null);
    setDeletingId(sessionId);
    try {
      await deleteSshSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <h1 className="mb-4 text-2xl font-semibold text-slate-900 dark:text-slate-100">
        SSH sessions
      </h1>
      <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
        Audited VM access via ssh-gateway. Use <strong>Play</strong> for in-browser replay or{" "}
        <strong>Download</strong> for the raw asciicast file. Indexed in Elasticsearch (
        <code className="text-xs">huy-sessions-*</code>).
      </p>
      {error && (
        <p className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {error}
        </p>
      )}
      {downloadError && (
        <p className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {downloadError}
        </p>
      )}
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950">
            <tr>
              <th className="px-4 py-2">VM</th>
              <th className="px-4 py-2">User</th>
              <th className="px-4 py-2">Linux</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Started</th>
              <th className="px-4 py-2">Terminal</th>
              <th className="px-4 py-2">Replay</th>
              <th className="px-4 py-2">Delete</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id} className="border-b border-slate-100 dark:border-slate-800">
                <td className="px-4 py-2 font-mono">{s.vm_name}</td>
                <td className="px-4 py-2">{s.user_email || s.user_username}</td>
                <td className="px-4 py-2 font-mono">{s.linux_user}</td>
                <td className="px-4 py-2">{s.status}</td>
                <td className="px-4 py-2">{new Date(s.started_at).toLocaleString()}</td>
                <td className="px-4 py-2">
                  {showConnect && s.status === "active" ? (
                    <Link
                      to="/access/terminal/$sessionId"
                      params={{ sessionId: s.id }}
                      className="text-emerald-600 hover:underline dark:text-emerald-400"
                    >
                      Open
                    </Link>
                  ) : (
                    <span className="text-slate-400">—</span>
                  )}
                </td>
                <td className="px-4 py-2 space-x-3">
                  <Link
                    to="/access/recording/$sessionId"
                    params={{ sessionId: s.id }}
                    className="text-emerald-600 hover:underline dark:text-emerald-400"
                  >
                    Play
                  </Link>
                  <button
                    type="button"
                    className="text-slate-600 hover:underline disabled:opacity-50 dark:text-slate-400"
                    disabled={downloadingId === s.id}
                    onClick={() => void handleDownload(s.id)}
                  >
                    {downloadingId === s.id ? "Downloading…" : "Download"}
                  </button>
                </td>
                <td className="px-4 py-2">
                  <button
                    type="button"
                    className="text-red-600 hover:underline disabled:opacity-50 dark:text-red-400"
                    disabled={deletingId === s.id}
                    onClick={() => void handleDelete(s.id, s.vm_name)}
                  >
                    {deletingId === s.id ? "Deleting…" : "Delete"}
                  </button>
                </td>
              </tr>
            ))}
            {!sessions.length && !error && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-slate-500">
                  No sessions yet. Open a VM from <strong>Projects → Connect</strong> or run{" "}
                  <code className="text-xs">huy ssh VM --project ID</code>.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
