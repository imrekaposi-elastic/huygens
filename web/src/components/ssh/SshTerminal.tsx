import { useEffect, useRef } from "react";
import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import "@xterm/xterm/css/xterm.css";
import { getAccessToken } from "@/auth/token";

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
      theme: { background: "#0f172a" },
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(el);
    fit.fit();
    termRef.current = term;

    const ws = new WebSocket(wsUrl(sessionId, token));
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      term.writeln("\r\n\x1b[32mConnected (audited session)\x1b[0m\r\n");
    };

    ws.onmessage = (ev) => {
      if (typeof ev.data === "string") {
        if (ev.data.startsWith("session failed:") || ev.data.startsWith("relay")) {
          onError?.(ev.data);
        }
        term.write(ev.data);
        return;
      }
      term.write(new Uint8Array(ev.data as ArrayBuffer));
    };

    ws.onerror = () => onError?.("WebSocket error");
    ws.onclose = () => {
      term.writeln("\r\n\x1b[33mSession closed.\x1b[0m");
      onClose?.();
    };

    const onData = term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });

    const onResize = () => fit.fit();
    window.addEventListener("resize", onResize);

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
    />
  );
}
