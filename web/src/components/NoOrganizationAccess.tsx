export function NoOrganizationAccess() {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="max-w-md rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-8 text-center">
        <h1 className="text-xl font-semibold text-slate-800 dark:text-slate-200">No organization access</h1>
        <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">
          Your account is not a member of any organization. Ask a platform administrator to
          create an organization and add you.
        </p>
      </div>
    </div>
  );
}
