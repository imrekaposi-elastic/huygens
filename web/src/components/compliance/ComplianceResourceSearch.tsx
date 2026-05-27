import { useEffect, useId, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ComplianceExplorerSuggestion } from "@/api/types";

export type ResourceSearchValue = {
  query: string;
  resourceKey: string;
  label: string;
};

type Props = {
  organizationId: string;
  value: ResourceSearchValue;
  resourceType?: "" | "vm" | "network" | "project";
  onChange: (next: ResourceSearchValue) => void;
};

export function ComplianceResourceSearch({
  organizationId,
  value,
  resourceType,
  onChange,
}: Props) {
  const listId = useId();
  const wrapRef = useRef<HTMLDivElement>(null);
  const [input, setInput] = useState(value.label || value.query);
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(input.trim()), 200);
    return () => window.clearTimeout(timer);
  }, [input]);

  useEffect(() => {
    if (value.label) {
      setInput(value.label);
      return;
    }
    setInput(value.query);
  }, [value.label, value.query, value.resourceKey]);

  const suggest = useQuery({
    queryKey: [
      "compliance-explorer-suggest",
      organizationId,
      debounced,
      resourceType || "all",
    ],
    queryFn: () =>
      api.complianceExplorerSuggest(organizationId, {
        q: debounced,
        resource_type: resourceType || undefined,
        limit: 12,
      }),
    enabled: !!organizationId && debounced.length >= 1 && open,
  });

  const items = suggest.data?.suggestions ?? [];
  const showList =
    open && debounced.length >= 1 && (suggest.isFetching || items.length > 0);

  useEffect(() => {
    function onDocClick(event: MouseEvent) {
      if (!wrapRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    setHighlight(0);
  }, [debounced, items.length]);

  function pick(item: ComplianceExplorerSuggestion) {
    onChange({ query: "", resourceKey: item.resource_key, label: item.label });
    setInput(item.label);
    setOpen(false);
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (!showList || !items.length) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlight((h) => Math.min(h + 1, items.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (event.key === "Enter" && items[highlight]) {
      event.preventDefault();
      pick(items[highlight]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={wrapRef} className="relative md:col-span-2 lg:col-span-3">
      <label className="block text-sm">
        Resource search
        <div className="relative mt-1">
          <input
            type="search"
            autoComplete="off"
            role="combobox"
            aria-expanded={showList}
            aria-controls={listId}
            aria-autocomplete="list"
            className="w-full min-h-10 rounded-lg border border-slate-300 bg-slate-50 py-2 pl-3 pr-20 dark:border-slate-700 dark:bg-slate-800"
            value={input}
            placeholder="Type e.g. dev — select a match or run filter"
            onChange={(e) => {
              const next = e.target.value;
              setInput(next);
              onChange({ query: next, resourceKey: "", label: "" });
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            onKeyDown={onKeyDown}
          />
          {(value.resourceKey || input) && (
            <button
              type="button"
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded px-2 py-0.5 text-xs text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700"
              onClick={() => {
                setInput("");
                onChange({ query: "", resourceKey: "", label: "" });
                setOpen(false);
              }}
            >
              Clear
            </button>
          )}
        </div>
      </label>

      {showList && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-30 mt-1 max-h-56 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white py-1 shadow-lg dark:border-slate-700 dark:bg-slate-900"
        >
          {suggest.isFetching && (
            <li className="px-3 py-2 text-xs text-slate-500">Searching…</li>
          )}
          {!suggest.isFetching &&
            items.map((item, index) => (
              <li key={item.resource_key} role="presentation">
                <button
                  type="button"
                  role="option"
                  aria-selected={index === highlight}
                  className={`block w-full px-3 py-2 text-left text-sm ${
                    index === highlight
                      ? "bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100"
                      : "text-slate-800 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800"
                  }`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    pick(item);
                  }}
                  onMouseEnter={() => setHighlight(index)}
                >
                  {item.label}
                </button>
              </li>
            ))}
          {!suggest.isFetching && items.length === 0 && (
            <li className="px-3 py-2 text-xs text-slate-500">No matching resources</li>
          )}
        </ul>
      )}
    </div>
  );
}
