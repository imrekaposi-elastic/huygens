import type { ReactNode } from "react";

export function FieldLabel({
  icon,
  children,
  className = "block text-sm",
}: {
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span className={`${className} flex items-center gap-2`}>
      {icon && <span className="shrink-0 text-slate-500 dark:text-slate-500">{icon}</span>}
      <span className="flex-1">{children}</span>
    </span>
  );
}
