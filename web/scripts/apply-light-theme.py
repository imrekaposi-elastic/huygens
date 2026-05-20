#!/usr/bin/env python3
"""Add Tailwind light defaults + dark: variants for existing slate utility classes."""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"

# (pattern, replacement) — longest / most specific first
REPLACEMENTS: list[tuple[str, str]] = [
    (r"bg-slate-900/80", r"bg-white/95 dark:bg-slate-900/80"),
    (r"bg-slate-900/50", r"bg-slate-100/90 dark:bg-slate-900/50"),
    (r"bg-slate-950/50", r"bg-red-50/90 dark:bg-red-950/50"),
    (r"bg-slate-950/40", r"bg-red-50 dark:bg-red-950/40"),
    (r"bg-red-950/50", r"bg-red-50/90 dark:bg-red-950/50"),
    (r"bg-red-950/40", r"bg-red-50 dark:bg-red-950/40"),
    (r"bg-slate-800/60", r"bg-slate-100 dark:bg-slate-800/60"),
    (r"bg-slate-950", r"bg-slate-100 dark:bg-slate-950"),
    (r"bg-slate-900", r"bg-white dark:bg-slate-900"),
    (r"bg-slate-800", r"bg-slate-50 dark:bg-slate-800"),
    (r"bg-black/60", r"bg-slate-900/40 dark:bg-black/60"),
    (r"divide-slate-800", r"divide-slate-200 dark:divide-slate-800"),
    (r"border-red-900/80", r"border-red-300 dark:border-red-900/80"),
    (r"border-slate-800", r"border-slate-200 dark:border-slate-800"),
    (r"border-slate-700", r"border-slate-300 dark:border-slate-700"),
    (r"border-slate-600", r"border-slate-300 dark:border-slate-600"),
    (r"hover:bg-red-950/40", r"hover:bg-red-100 dark:hover:bg-red-950/40"),
    (r"hover:bg-slate-800", r"hover:bg-slate-100 dark:hover:bg-slate-800"),
    (r"hover:bg-slate-700", r"hover:bg-slate-200 dark:hover:bg-slate-700"),
    (r"hover:text-white", r"hover:text-slate-900 dark:hover:text-white"),
    (r"hover:text-slate-200", r"hover:text-slate-800 dark:hover:text-slate-200"),
    (r"text-emerald-400/90", r"text-emerald-600/90 dark:text-emerald-400/90"),
    (r"text-emerald-400", r"text-emerald-600 dark:text-emerald-400"),
    (r"text-emerald-300", r"text-emerald-700 dark:text-emerald-300"),
    (r"text-amber-400", r"text-amber-700 dark:text-amber-400"),
    (r"text-amber-300", r"text-amber-800 dark:text-amber-300"),
    (r"text-red-400", r"text-red-600 dark:text-red-400"),
    (r"text-red-300", r"text-red-700 dark:text-red-300"),
    (r"text-white", r"text-slate-900 dark:text-white"),
    (r"text-slate-100", r"text-slate-900 dark:text-slate-100"),
    (r"text-slate-200", r"text-slate-800 dark:text-slate-200"),
    (r"text-slate-300", r"text-slate-700 dark:text-slate-300"),
    (r"text-slate-400", r"text-slate-600 dark:text-slate-400"),
    (r"text-slate-500", r"text-slate-500 dark:text-slate-500"),
    (r"bg-emerald-900/40", r"bg-emerald-100 dark:bg-emerald-900/40"),
]


def transform(content: str) -> str:
    for pattern, repl in REPLACEMENTS:
        # Skip tokens already prefixed with dark:
        def sub(m: re.Match[str]) -> str:
            start = m.start()
            prefix = content[max(0, start - 5) : start]
            if "dark:" in prefix:
                return m.group(0)
            return repl

        content = re.sub(pattern, sub, content)
    # Collapse accidental double dark:dark:
    content = content.replace("dark:dark:", "dark:")
    return content


def main() -> None:
    skip = {"theme/storage.ts", "ThemeToggle.tsx"}
    for path in sorted(SRC.rglob("*.tsx")) + sorted(SRC.rglob("*.ts")):
        rel = path.relative_to(SRC.parent)
        if any(s in str(rel) for s in skip):
            continue
        text = path.read_text()
        updated = transform(text)
        if updated != text:
            path.write_text(updated)
            print(f"updated {rel}")


if __name__ == "__main__":
    main()
