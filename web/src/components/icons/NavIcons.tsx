/** Inline nav icons (stroke, currentColor). */

import type { ReactNode } from "react";

type IconProps = { className?: string };

const base = "size-5 shrink-0";

export function HomeIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5z" strokeLinejoin="round" />
    </svg>
  );
}

export function CloudIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path
        d="M7 18h11a4 4 0 0 0 .5-8 5.5 5.5 0 0 0-10.6-1.8A3.5 3.5 0 0 0 7 18z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function GlobeIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" strokeLinecap="round" />
    </svg>
  );
}

/** Jigsaw tab + server stack for Fabric (agent technologies). */
export function AgentTechIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
      <path
        d="M4 6h5v2.2a1.2 1.2 0 0 0 2.4 0V6h1.1a1.2 1.2 0 0 1 0 2.4H11.4V11H4V6z"
        strokeLinejoin="round"
      />
      <rect x="13" y="5" width="7" height="3" rx="0.5" />
      <rect x="13" y="10" width="7" height="3" rx="0.5" />
      <rect x="13" y="15" width="7" height="3" rx="0.5" />
      <circle cx="8.2" cy="8.2" r="0.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function FolderIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path
        d="M4 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V7z"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function FolderOpenIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path
        d="M4 9V7a2 2 0 0 1 2-2h3l2 2h7a2 2 0 0 1 2 2v1M4 9h16l-1.2 8.4a1 1 0 0 1-1 .6H6.2a1 1 0 0 1-1-.6L4 9z"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function VmIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <rect x="3" y="4" width="18" height="12" rx="1.5" />
      <path d="M8 20h8M12 16v4" strokeLinecap="round" />
    </svg>
  );
}

export function NetworkIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <circle cx="6" cy="12" r="2.5" />
      <circle cx="18" cy="6" r="2.5" />
      <circle cx="18" cy="18" r="2.5" />
      <path d="M8.5 11 15 7M8.5 13l6.5 4" strokeLinecap="round" />
    </svg>
  );
}

export function CogIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <circle cx="12" cy="12" r="3" />
      <path
        d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** Inline icon for page titles — always small, never full-width. */
export function PageTitleIcon({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex h-5 w-5 shrink-0 items-center justify-center text-emerald-600/90 dark:text-emerald-400/90 [&>svg]:h-5 [&>svg]:w-5">
      {children}
    </span>
  );
}

export function PageTitle({
  icon,
  children,
}: {
  icon?: ReactNode;
  children: ReactNode;
}) {
  return (
    <h1 className="flex items-center gap-2 text-2xl font-semibold">
      {icon ? <PageTitleIcon>{icon}</PageTitleIcon> : null}
      {children}
    </h1>
  );
}

export function CdIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <circle cx="12" cy="12" r="8" />
      <circle cx="12" cy="12" r="2.5" />
    </svg>
  );
}

export function UsersIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <circle cx="9" cy="8" r="3" />
      <circle cx="17" cy="10" r="2.5" />
      <path d="M4 20c0-3 2.5-5 5-5s5 2 5 5M14 20c0-2.2 1.8-4 4-4" strokeLinecap="round" />
    </svg>
  );
}

export function ShieldIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <path d="M12 3 5 6v6c0 5 3.5 7.5 7 9 3.5-1.5 7-4 7-9V6l-7-3z" strokeLinejoin="round" />
    </svg>
  );
}

/** Compliance nav / page mark (checkmark in circle). */
export function CheckmarkIcon({ className = base }: IconProps) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12.5 10.5 15 16 9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
