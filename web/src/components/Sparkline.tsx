type Props = {
  values: number[];
  height?: number;
  className?: string;
  strokeClassName?: string;
};

export function Sparkline({
  values,
  height = 40,
  className = "",
  strokeClassName = "stroke-emerald-500 dark:stroke-emerald-400",
}: Props) {
  const width = 120;
  const data = values.length > 0 ? values : [0];
  const min = Math.min(...data);
  const max = Math.max(...data);
  const span = max - min || 1;
  const step = data.length > 1 ? width / (data.length - 1) : width;

  const points = data
    .map((v, i) => {
      const x = i * step;
      const y = height - ((v - min) / span) * (height - 4) - 2;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className={`w-full max-w-[140px] ${className}`}
      preserveAspectRatio="none"
      aria-hidden
    >
      <polyline
        fill="none"
        className={strokeClassName}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
    </svg>
  );
}
