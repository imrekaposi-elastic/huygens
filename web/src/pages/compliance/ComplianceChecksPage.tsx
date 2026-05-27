import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { canManageComplianceCatalog } from "@/auth/permissions";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";
import { ComplianceChecksPanel } from "@/components/compliance/ComplianceChecksPanel";

export function ComplianceChecksPage() {
  const { user, selectedOrgId } = useAuth();
  const organizationId = selectedOrgId ?? "";
  const platformAdmin = isPlatformAdmin(getAccessToken());
  const canManage = canManageComplianceCatalog(user, organizationId, platformAdmin);
  const [err, setErr] = useState<string | null>(null);

  const catalog = useQuery({
    queryKey: ["compliance-catalog", organizationId],
    queryFn: () => api.listComplianceCatalog(organizationId),
  });

  const catalogOptions = (catalog.data ?? []).map((i) => ({ id: i.id, name: i.name }));

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Track review cycles and owners for catalog standards. Expiring checks appear in the
        overview KPIs.
      </p>
      <ComplianceChecksPanel
        organizationId={organizationId}
        canManage={canManage}
        catalogItemOptions={catalogOptions}
        onError={setErr}
        defaultOpen
      />
      {err && <p className="text-sm text-red-600 dark:text-red-400">{err}</p>}
    </div>
  );
}
