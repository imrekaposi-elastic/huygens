import { useEffect, useRef, useState } from "react";
import * as AsciinemaPlayer from "asciinema-player";
import "asciinema-player/dist/bundle/asciinema-player.css";

type Props = {
  src: string;
  title?: string;
};

export function SshRecordingPlayer({ src, title }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<{ dispose: () => void } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    setError(null);
    host.innerHTML = "";

    try {
      playerRef.current = AsciinemaPlayer.create(src, host, {
        autoPlay: true,
        loop: false,
        theme: "asciinema",
        controls: true,
        terminalFontSize: "14px",
        fit: "width",
        poster: "npt:0:01",
        idleTimeLimit: 2,
      }) as { dispose: () => void };
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load recording");
    }

    return () => {
      playerRef.current?.dispose();
      playerRef.current = null;
      host.innerHTML = "";
    };
  }, [src]);

  return (
    <div className="space-y-2">
      {title ? (
        <p className="text-sm text-slate-600 dark:text-slate-400">
          {title}
        </p>
      ) : null}
      {error ? (
        <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {error}
        </p>
      ) : null}
      <div
        ref={hostRef}
        className="overflow-hidden rounded border border-slate-700 bg-slate-950"
      />
    </div>
  );
}
