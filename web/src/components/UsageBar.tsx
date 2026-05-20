type Segment = { label: string; value: number; className: string };

type Props = {
  segments: Segment[];
  total?: number;
};

export function UsageBar({ segments, total }: Props) {
  const sum = total ?? segments.reduce((a, s) => a + Math.max(0, s.value), 0);
  if (sum <= 0) {
    return <div className="h-3 rounded-full bg-slate-200 dark:bg-slate-800" />;
  }

  return (
    <div className="flex h-3 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
      {segments.map((s) => {
        const pct = (Math.max(0, s.value) / sum) * 100;
        if (pct <= 0) return null;
        return (
          <div
            key={s.label}
            className={s.className}
            style={{ width: `${pct}%` }}
            title={`${s.label}: ${pct.toFixed(1)}%`}
          />
        );
      })}
    </div>
  );
}
