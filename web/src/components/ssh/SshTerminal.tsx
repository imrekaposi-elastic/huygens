import { useEffect, useRef } from "react";
import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import { getAccessToken } from "@/auth/token";
import { explainSshSessionError } from "@/lib/sshErrors";

type Props = {
  sessionId: string;
  onClose?: () => void;
  onError?: (message: string) => void;
};

function wsUrl(sessionId: string, token: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const q = new URLSearchParams({ access_token: token });
  return `${proto}//${window.location.host}/api/v1/ssh/sessions/${encodeURIComponent(sessionId)}/ws?${q}`;
}

const encoder = new TextEncoder();

export function SshTerminal({ sessionId, onClose, onError }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const token = getAccessToken();
    if (!token) {
      onError?.("Not logged in");
      return;
    }

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      theme: { background: "#0f172a", foreground: "#e2e8f0", cursor: "#e2e8f0" },
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(el);
    fit.fit();
    termRef.current = term;
    term.writeln("\x1b[90mConnecting to VM…\x1b[0m");

    const ws = new WebSocket(wsUrl(sessionId, token));
    ws.binaryType = "arraybuffer";

    const sendResize = () => {
      if (ws.readyState !== WebSocket.OPEN) return;
      const payload = JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows });
      ws.send(encoder.encode("\x00" + payload));
    };

    ws.onopen = () => {
      fit.fit();
      sendResize();
    };

    ws.onmessage = async (ev) => {
      if (typeof ev.data === "string") {
        if (ev.data.startsWith("session failed:") || ev.data.startsWith("relay")) {
          onError?.(explainSshSessionError(ev.data));
          term.writeln(`\r\n\x1b[31m${ev.data}\x1b[0m`);
          return;
        }
        if (ev.data.startsWith("huy:ready")) {
          term.write("\r\n\x1b[32mConnected (audited session)\x1b[0m\r\n");
          term.focus();
          return;
        }
        term.write(ev.data);
        return;
      }
      const bytes =
        ev.data instanceof Blob
          ? new Uint8Array(await ev.data.arrayBuffer())
          : new Uint8Array(ev.data as ArrayBuffer);
      term.write(bytes);
    };

    ws.onerror = () => onError?.("WebSocket error");
    ws.onclose = () => {
      term.writeln("\r\n\x1b[33mSession closed.\x1b[0m");
      onClose?.();
    };

    const onData = term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(encoder.encode(data));
      }
    });

    const onResize = () => {
      fit.fit();
      sendResize();
    };
    window.addEventListener("resize", onResize);
    term.onResize(() => sendResize());

    return () => {
      onData.dispose();
      window.removeEventListener("resize", onResize);
      ws.close();
      term.dispose();
      termRef.current = null;
    };
  }, [sessionId, onClose, onError]);

  return (
    <div
      ref={containerRef}
      className="h-[min(70vh,520px)] w-full overflow-hidden rounded border border-slate-700 bg-slate-900 p-1"
      onClick={() => termRef.current?.focus()}
    />
  );
}
