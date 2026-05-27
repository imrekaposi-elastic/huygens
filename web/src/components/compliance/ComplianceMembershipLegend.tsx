type Props = {
  className?: string;
  compact?: boolean;
  /** Show blue “all children compliant” key (project aggregate). */
  showAggregate?: boolean;
};

/** Legend for direct (green), inherited (grey), and project aggregate (blue) membership. */
export function ComplianceMembershipLegend({
  className = "",
  compact = false,
  showAggregate = false,
}: Props) {
  return (
    <div
      className={`flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-600 dark:text-slate-400 ${className}`}
      role="note"
      aria-label="Compliance membership legend"
    >
      <span className="flex items-center gap-2">
        <MembershipCheckbox variant="direct" />
        <span>{compact ? "Direct" : "Direct membership"}</span>
      </span>
      <span className="flex items-center gap-2">
        <MembershipCheckbox variant="inherited" />
        <span>{compact ? "Inherited" : "Inherited membership"}</span>
      </span>
      {showAggregate && (
        <span className="flex items-center gap-2">
          <MembershipCheckbox variant="aggregate" />
          <span>
            {compact ? "All children" : "All child objects are compliant"}
          </span>
        </span>
      )}
    </div>
  );
}

export function MembershipCheckbox({
  variant,
  className = "",
}: {
  variant: "direct" | "inherited" | "aggregate" | "none";
  className?: string;
}) {
  const checked = variant !== "none";
  const boxClass =
    variant === "direct"
      ? "border-emerald-500 bg-emerald-50 dark:border-emerald-600 dark:bg-emerald-950/50"
      : variant === "aggregate"
        ? "border-blue-500 bg-blue-50 dark:border-blue-600 dark:bg-blue-950/50"
        : variant === "inherited"
          ? "border-slate-300 bg-slate-100 dark:border-slate-600 dark:bg-slate-700/80"
          : "border-slate-300 bg-white dark:border-slate-600 dark:bg-slate-800";
  const checkStroke =
    variant === "direct"
      ? "#047857"
      : variant === "aggregate"
        ? "#2563eb"
        : "#64748b";

  return (
    <span
      className={`inline-flex size-4 shrink-0 items-center justify-center rounded border ${boxClass} ${className}`}
      aria-hidden
    >
      {checked && (
        <svg className="size-3" viewBox="0 0 12 12" fill="none">
          <path
            d="M2 6l3 3 5-5"
            stroke={checkStroke}
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </span>
  );
}
