import { useRef } from "react";

type Props = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  placeholder?: string;
  rows?: number;
  hint?: string;
};

export function FileTextField({
  label,
  value,
  onChange,
  required,
  placeholder,
  rows = 8,
  hint,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  function loadFile(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") onChange(reader.result);
    };
    reader.readAsText(file);
  }

  return (
    <label className="block text-sm">
      <span className="text-slate-700 dark:text-slate-300">{label}</span>
      {hint && <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-500">{hint}</span>}
      <div className="mt-1 flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded border border-slate-300 dark:border-slate-600 px-3 py-1 text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:bg-slate-800"
          onClick={() => inputRef.current?.click()}
        >
          Load from file…
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".yaml,.yml,.txt,.cfg,.cloud-config,text/*"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) loadFile(file);
            e.target.value = "";
          }}
        />
      </div>
      <textarea
        className="mt-2 w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-950 px-3 py-2 font-mono text-xs text-slate-800 dark:text-slate-200"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        rows={rows}
        spellCheck={false}
      />
    </label>
  );
}
