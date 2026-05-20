import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/auth/AuthContext";
import { isValidOrgSlug, slugFromName } from "@/auth/setup";
import { api, ApiError } from "@/api/client";

const STEPS = [
  { id: "welcome", title: "Welcome" },
  { id: "organization", title: "Organization" },
  { id: "project", title: "First project" },
  { id: "security", title: "Security" },
  { id: "done", title: "Finish" },
] as const;

type StepId = (typeof STEPS)[number]["id"];

export function PlatformSetupPage() {
  const navigate = useNavigate();
  const { refresh, setSelectedOrgId } = useAuth();
  const [step, setStep] = useState<StepId>("welcome");
  const [orgName, setOrgName] = useState("");
  const [orgSlug, setOrgSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [projectName, setProjectName] = useState("");
  const [projectSlug, setProjectSlug] = useState("");
  const [projectSlugTouched, setProjectSlugTouched] = useState(false);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stepIndex = STEPS.findIndex((s) => s.id === step);

  function goBack() {
    const prev = STEPS[stepIndex - 1];
    if (prev) setStep(prev.id);
  }

  async function createOrganization() {
    const slug = orgSlug.trim() || slugFromName(orgName);
    if (!orgName.trim()) {
      setError("Organization name is required.");
      return;
    }
    if (!isValidOrgSlug(slug)) {
      setError("Slug must be lowercase letters, numbers, and hyphens (e.g. acme-corp).");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const org = await api.createOrganization({ name: orgName.trim(), slug });
      setOrgId(org.id);
      setSelectedOrgId(org.id);
      setStep("project");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create organization");
    } finally {
      setBusy(false);
    }
  }

  async function createProject(skip: boolean) {
    if (skip || !projectName.trim()) {
      setStep("security");
      return;
    }
    const slug = projectSlug.trim() || slugFromName(projectName);
    if (!orgId) {
      setError("Organization missing — go back and create it first.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      await api.createProject({
        organization_id: orgId,
        name: projectName.trim(),
        slug,
      });
      setStep("security");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create project");
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    setBusy(true);
    try {
      await refresh();
      void navigate({ to: "/", replace: true });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900">
      <div className="mx-auto max-w-2xl px-4 py-10">
        <header className="mb-8 text-center">
          <p className="text-sm font-medium uppercase tracking-wider text-emerald-500">
            Huygens setup
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900 dark:text-white">Configure your control plane</h1>
          <p className="mt-2 text-slate-600 dark:text-slate-400">
            Step {stepIndex + 1} of {STEPS.length} — {STEPS[stepIndex]?.title}
          </p>
          <div className="mt-6 flex justify-center gap-2">
            {STEPS.map((s, i) => (
              <div
                key={s.id}
                className={`h-2 w-10 rounded-full transition-colors ${
                  i <= stepIndex ? "bg-emerald-500" : "bg-slate-700"
                }`}
                aria-hidden
              />
            ))}
          </div>
        </header>

        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90 p-8 shadow-xl">
          {error && (
            <p className="mb-4 rounded-lg bg-red-50/90 dark:bg-red-950/50 px-4 py-3 text-sm text-red-700 dark:text-red-300">{error}</p>
          )}

          {step === "welcome" && (
            <div className="space-y-4 text-slate-700 dark:text-slate-300">
              <p>
                This wizard walks you through the minimum setup for a new Huygens deployment —
                similar to first-launch setup on other platforms.
              </p>
              <ul className="list-inside list-disc space-y-2 text-sm text-slate-600 dark:text-slate-400">
                <li>Create your first <strong className="text-slate-700 dark:text-slate-300">organization</strong> (tenant boundary)</li>
                <li>Optionally add a <strong className="text-slate-700 dark:text-slate-300">project</strong> for workloads</li>
                <li>Review <strong className="text-slate-700 dark:text-slate-300">security</strong> recommendations before going live</li>
              </ul>
              <p className="text-sm text-slate-500 dark:text-slate-500">
                You can add agents, networks, and more from the console after setup. Use{" "}
                <strong className="text-slate-600 dark:text-slate-400">New</strong> in the header anytime to create
                additional organizations.
              </p>
            </div>
          )}

          {step === "organization" && (
            <div className="space-y-4">
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Organizations isolate tenants. Every project and inventory view belongs to one
                organization.
              </p>
              <label className="block text-sm">
                Organization name
                <input
                  className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                  value={orgName}
                  onChange={(e) => {
                    setOrgName(e.target.value);
                    if (!slugTouched) setOrgSlug(slugFromName(e.target.value));
                  }}
                  placeholder="Acme Corp"
                  autoFocus
                />
              </label>
              <label className="block text-sm">
                URL slug
                <input
                  className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
                  value={orgSlug}
                  onChange={(e) => {
                    setSlugTouched(true);
                    setOrgSlug(e.target.value);
                  }}
                  placeholder="acme-corp"
                />
              </label>
            </div>
          )}

          {step === "project" && (
            <div className="space-y-4">
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Projects group agents and VMs. You can skip this and create projects later under{" "}
                <span className="text-slate-700 dark:text-slate-300">Projects</span>.
              </p>
              <label className="block text-sm">
                Project name
                <input
                  className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3"
                  value={projectName}
                  onChange={(e) => {
                    setProjectName(e.target.value);
                    if (!projectSlugTouched) setProjectSlug(slugFromName(e.target.value));
                  }}
                  placeholder="Production"
                />
              </label>
              <label className="block text-sm">
                Project slug
                <input
                  className="mt-1 w-full min-h-11 rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 font-mono text-sm"
                  value={projectSlug}
                  onChange={(e) => {
                    setProjectSlugTouched(true);
                    setProjectSlug(e.target.value);
                  }}
                  placeholder="production"
                />
              </label>
            </div>
          )}

          {step === "security" && (
            <div className="space-y-4 text-sm text-slate-700 dark:text-slate-300">
              <p>Before exposing this stack beyond local development:</p>
              <ul className="list-inside list-disc space-y-2 text-slate-600 dark:text-slate-400">
                <li>
                  Set strong values in <code className="text-emerald-600 dark:text-emerald-400">.env</code> for{" "}
                  <code className="text-slate-700 dark:text-slate-300">BOOTSTRAP_ADMIN_PASSWORD</code> and{" "}
                  <code className="text-slate-700 dark:text-slate-300">JWT_SECRET</code> (32+ characters)
                </li>
                <li>Align service tokens across registry, inventory, and projects</li>
                <li>Enable OIDC / Keycloak when you are ready for SSO (<code className="text-slate-700 dark:text-slate-300">docker compose --profile sso up</code>)</li>
              </ul>
            </div>
          )}

          {step === "done" && (
            <div className="space-y-3 text-center text-slate-700 dark:text-slate-300">
              <p className="text-lg font-medium text-emerald-600 dark:text-emerald-400">Setup complete</p>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {orgName ? (
                  <>
                    Organization <strong className="text-slate-900 dark:text-white">{orgName}</strong> is ready.
                  </>
                ) : (
                  "Your organization is ready."
                )}{" "}
                Open the dashboard to view inventory and manage projects.
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-500">
                Use <strong className="text-slate-600 dark:text-slate-400">New</strong> / <strong className="text-slate-600 dark:text-slate-400">Delete</strong>{" "}
                next to the organization selector in the header to manage tenants later.
              </p>
            </div>
          )}

          <div className="mt-8 flex flex-wrap gap-3">
            {stepIndex > 0 && step !== "done" && (
              <button
                type="button"
                onClick={goBack}
                disabled={busy}
                className="min-h-11 rounded-lg border border-slate-300 dark:border-slate-600 px-5 text-sm hover:bg-slate-50 dark:bg-slate-800 disabled:opacity-50"
              >
                Back
              </button>
            )}
            <div className="flex-1" />
            {step === "welcome" && (
              <button
                type="button"
                onClick={() => setStep("organization")}
                className="min-h-11 rounded-lg bg-emerald-600 px-6 font-medium hover:bg-emerald-500"
              >
                Get started
              </button>
            )}
            {step === "organization" && (
              <button
                type="button"
                onClick={() => void createOrganization()}
                disabled={busy}
                className="min-h-11 rounded-lg bg-emerald-600 px-6 font-medium hover:bg-emerald-500 disabled:opacity-50"
              >
                {busy ? "Creating…" : "Continue"}
              </button>
            )}
            {step === "project" && (
              <>
                <button
                  type="button"
                  onClick={() => void createProject(true)}
                  disabled={busy}
                  className="min-h-11 rounded-lg border border-slate-300 dark:border-slate-600 px-5 text-sm hover:bg-slate-50 dark:bg-slate-800"
                >
                  Skip for now
                </button>
                <button
                  type="button"
                  onClick={() => void createProject(false)}
                  disabled={busy}
                  className="min-h-11 rounded-lg bg-emerald-600 px-6 font-medium hover:bg-emerald-500 disabled:opacity-50"
                >
                  {busy ? "Saving…" : projectName.trim() ? "Continue" : "Continue without project"}
                </button>
              </>
            )}
            {step === "security" && (
              <button
                type="button"
                onClick={() => setStep("done")}
                className="min-h-11 rounded-lg bg-emerald-600 px-6 font-medium hover:bg-emerald-500"
              >
                Continue
              </button>
            )}
            {step === "done" && (
              <button
                type="button"
                onClick={() => void finish()}
                disabled={busy}
                className="min-h-11 rounded-lg bg-emerald-600 px-6 font-medium hover:bg-emerald-500 disabled:opacity-50"
              >
                {busy ? "Opening console…" : "Open console"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
