import type { ReactNode } from "react";

type Props = {
  title: string;
  description?: string;
  onNew: () => void;
  newLabel?: string;
  loading?: boolean;
  children: ReactNode;
};

export function ResourceList({
  title,
  description,
  onNew,
  newLabel = "New",
  loading,
  children,
}: Props) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-medium">{title}</h2>
          {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
        </div>
        <button
          type="button"
          onClick={onNew}
          className="min-h-10 rounded-lg bg-emerald-600 px-4 text-sm font-medium hover:bg-emerald-500"
        >
          {newLabel}
        </button>
      </div>
      {loading ? (
        <p className="text-slate-400">Loading…</p>
      ) : (
        <ul className="divide-y divide-slate-800 rounded-lg border border-slate-800 bg-slate-900/50">
          {children}
        </ul>
      )}
    </div>
  );
}

export function ResourceListItem({
  name,
  subtitle,
  onEdit,
  onDelete,
  deleteLabel = "Delete",
  extra,
}: {
  name: string;
  subtitle?: string;
  onEdit: () => void;
  onDelete?: () => void;
  deleteLabel?: string;
  extra?: ReactNode;
}) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
      <div className="min-w-0">
        <p className="font-medium text-slate-100">{name}</p>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
        {extra}
      </div>
      <div className="flex shrink-0 gap-2">
        <button
          type="button"
          onClick={onEdit}
          className="rounded border border-slate-600 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-800"
        >
          Edit
        </button>
        {onDelete && (
          <button
            type="button"
            onClick={onDelete}
            className="rounded border border-red-900/80 px-3 py-1.5 text-sm text-red-300 hover:bg-red-950/40"
          >
            {deleteLabel}
          </button>
        )}
      </div>
    </li>
  );
}

export function ResourceListEmpty({ message }: { message: string }) {
  return <li className="px-4 py-8 text-center text-sm text-slate-500">{message}</li>;
}
