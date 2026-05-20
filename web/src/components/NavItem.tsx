import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";

type Props = {
  to: string;
  label: string;
  icon: ReactNode;
  active: boolean;
};

function navClass(active: boolean) {
  return `flex min-h-11 items-center gap-2.5 rounded-lg px-3 py-2 text-sm md:min-h-0 ${
    active
      ? "bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-white"
      : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800/60"
  }`;
}

export function NavItem({ to, label, icon, active }: Props) {
  return (
    <Link to={to} className={navClass(active)}>
      <span className={active ? "text-emerald-600 dark:text-emerald-400" : "text-slate-500 dark:text-slate-500"}>{icon}</span>
      {label}
    </Link>
  );
}
