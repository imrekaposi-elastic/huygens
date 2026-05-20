import { useEffect, useRef, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { AgentOut, HostMetricsSnapshot } from "@/api/types";
import { Sparkline } from "@/components/Sparkline";
import { UsageBar } from "@/components/UsageBar";
import {
  bytesPerSecToMbps,
  formatBytes,
  formatIops,
  formatMegabitsPerSec,
  formatPercent,
} from "@/lib/formatBytes";

const POLL_MS = 5000;
const HISTORY_MAX = 72;

type RateSample = {
  networkIn: number | null;
  networkOut: number | null;
  iopsRead: number | null;
  iopsWrite: number | null;
};

function deltaRate(current: number, previous: number | undefined, dtSec: number): number | null {
  if (previous === undefined || dtSec <= 0 || current < previous) return null;
  return (current - previous) / dtSec;
}

function pushHistory(arr: number[], value: number, max = HISTORY_MAX) {
  const next = [...arr, value];
  return next.length > max ? next.slice(-max) : next;
}

type Props = {
  agent: AgentOut;
  onClose: () => void;
};

export function AgentMetricsPanel({ agent, onClose }: Props) {
  const prevRef = useRef<HostMetricsSnapshot | null>(null);
  const prevTimeRef = useRef<number | null>(null);
  const [history, setHistory] = useState({
    cpu: [] as number[],
    vmsRunning: [] as number[],
    netIn: [] as number[],
    netOut: [] as number[],
    iopsRead: [] as number[],
    iopsWrite: [] as number[],
  });
  const [rates, setRates] = useState<RateSample>({
    networkIn: null,
    networkOut: null,
    iopsRead: null,
    iopsWrite: null,
  });

  const { data, error, isFetching, dataUpdatedAt } = useQuery({
    queryKey: ["agent-metrics", agent.id],
    queryFn: () => api.agentMetrics(agent.id),
    refetchInterval: POLL_MS,
    refetchIntervalInBackground: true,
  });

  useEffect(() => {
    if (!data) return;
    const now = dataUpdatedAt || Date.now();
    const prev = prevRef.current;
    const prevTime = prevTimeRef.current;
    const dtSec = prevTime != null ? (now - prevTime) / 1000 : 0;

    let netIn: number | null = null;
    let netOut: number | null = null;
    let iopsR: number | null = null;
    let iopsW: number | null = null;

    if (prev && dtSec > 0) {
      if (data.network && prev.network) {
        netIn = deltaRate(data.network.bytes_recv_total, prev.network.bytes_recv_total, dtSec);
        netOut = deltaRate(data.network.bytes_sent_total, prev.network.bytes_sent_total, dtSec);
      }
      if (data.disk_io && prev.disk_io) {
        iopsR = deltaRate(data.disk_io.read_ops_total, prev.disk_io.read_ops_total, dtSec);
        iopsW = deltaRate(data.disk_io.write_ops_total, prev.disk_io.write_ops_total, dtSec);
      }
    }

    setRates({ networkIn: netIn, networkOut: netOut, iopsRead: iopsR, iopsWrite: iopsW });
    setHistory((h) => ({
      cpu: pushHistory(h.cpu, data.cpu_percent),
      vmsRunning: pushHistory(h.vmsRunning, data.vms.running),
      netIn: netIn != null ? pushHistory(h.netIn, bytesPerSecToMbps(netIn)) : h.netIn,
      netOut: netOut != null ? pushHistory(h.netOut, bytesPerSecToMbps(netOut)) : h.netOut,
      iopsRead: iopsR != null ? pushHistory(h.iopsRead, iopsR) : h.iopsRead,
      iopsWrite: iopsW != null ? pushHistory(h.iopsWrite, iopsW) : h.iopsWrite,
    }));

    prevRef.current = data;
    prevTimeRef.current = now;
  }, [data, dataUpdatedAt]);

  const mem = data?.memory;
  const disk = data?.disk;

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900/80">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            Performance — {agent.name}
          </h2>
          <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-400">
            Live from hypervisor · refreshes every {POLL_MS / 1000}s
            {isFetching && " · updating…"}
            {data && !data.libvirt_connected && (
              <span className="ml-2 text-amber-700 dark:text-amber-400">libvirt disconnected</span>
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="min-h-9 rounded-lg border border-slate-300 px-3 text-sm text-slate-700 hover:bg-slate-100 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
        >
          Close
        </button>
      </div>

      {error && (
        <p className="mt-3 text-sm text-red-600 dark:text-red-300">
          {error instanceof ApiError ? error.message : "Failed to load metrics"}
        </p>
      )}

      {!data && !error && <p className="mt-4 text-sm text-slate-600 dark:text-slate-400">Loading metrics…</p>}

      {data && (
        <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <MetricCard title="VMs running" value={String(data.vms.running)} sub={`${data.vms.total} total`}>
            <Sparkline values={history.vmsRunning} strokeClassName="stroke-sky-500 dark:stroke-sky-400" />
          </MetricCard>

          <MetricCard title="CPU usage" value={formatPercent(data.cpu_percent)}>
            <Sparkline values={history.cpu} />
          </MetricCard>

          <MetricCard
            title="Memory"
            value={mem ? formatBytes(mem.used_bytes) : "—"}
            sub={
              mem
                ? `free ${formatBytes(mem.available_bytes)} · VMs allocated ${formatBytes(mem.allocated_to_vms_bytes)}`
                : undefined
            }
          >
            {mem && (
              <div className="space-y-1">
                <UsageBar
                  total={mem.total_bytes}
                  segments={[
                    {
                      label: "Used",
                      value: mem.used_bytes,
                      className: "bg-amber-500/80",
                    },
                    {
                      label: "Available",
                      value: mem.available_bytes,
                      className: "bg-emerald-500/60",
                    },
                  ]}
                />
                <p className="text-xs text-slate-500 dark:text-slate-500">
                  Total {formatBytes(mem.total_bytes)} ({formatPercent(mem.usage_percent)} host)
                </p>
              </div>
            )}
          </MetricCard>

          <MetricCard
            title="Disk"
            value={disk ? formatBytes(disk.free_bytes) : "—"}
            sub={disk ? `free of ${formatBytes(disk.total_bytes)} on ${disk.mount}` : "No disk data"}
          >
            {disk && (
              <div className="space-y-1">
                <UsageBar
                  total={disk.total_bytes}
                  segments={[
                    { label: "Used", value: disk.used_bytes, className: "bg-violet-500/80" },
                    { label: "Free", value: disk.free_bytes, className: "bg-slate-400/40" },
                  ]}
                />
                <p className="text-xs text-slate-500">{formatPercent(disk.usage_percent)} used</p>
              </div>
            )}
          </MetricCard>

          <MetricCard
            title="Disk IOPS"
            value={
              rates.iopsRead != null || rates.iopsWrite != null
                ? `R ${formatIops(rates.iopsRead)} · W ${formatIops(rates.iopsWrite)}`
                : "…"
            }
            sub="Read / write operations per second"
          >
            <div className="flex gap-2">
              <div className="flex-1">
                <p className="mb-0.5 text-xs text-slate-500">Read</p>
                <Sparkline values={history.iopsRead} strokeClassName="stroke-violet-500" />
              </div>
              <div className="flex-1">
                <p className="mb-0.5 text-xs text-slate-500">Write</p>
                <Sparkline values={history.iopsWrite} strokeClassName="stroke-fuchsia-500" />
              </div>
            </div>
          </MetricCard>

          <MetricCard
            title="Network"
            value={
              rates.networkIn != null || rates.networkOut != null
                ? `↓ ${formatMegabitsPerSec(rates.networkIn)} · ↑ ${formatMegabitsPerSec(rates.networkOut)}`
                : "…"
            }
            sub="Megabits per second in (recv) / out (sent)"
          >
            <div className="flex gap-2">
              <div className="flex-1">
                <p className="mb-0.5 text-xs text-slate-500">In</p>
                <Sparkline values={history.netIn} strokeClassName="stroke-cyan-500" />
              </div>
              <div className="flex-1">
                <p className="mb-0.5 text-xs text-slate-500">Out</p>
                <Sparkline values={history.netOut} strokeClassName="stroke-orange-500" />
              </div>
            </div>
          </MetricCard>
        </div>
      )}
    </section>
  );
}

function MetricCard({
  title,
  value,
  sub,
  children,
}: {
  title: string;
  value: string;
  sub?: string;
  children: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-800 dark:bg-slate-950/40">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-500">
        {title}
      </p>
      <p className="mt-1 text-xl font-semibold text-slate-900 dark:text-white">{value}</p>
      {sub && <p className="text-xs text-slate-600 dark:text-slate-400">{sub}</p>}
      <div className="mt-2">{children}</div>
    </div>
  );
}
