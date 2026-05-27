import { useAuth } from "@/auth/AuthContext";
import { ComplianceExplorer } from "@/components/compliance/ComplianceExplorer";

export function ComplianceExplorerPage() {
  const { selectedOrgId } = useAuth();
  if (!selectedOrgId) return null;
  return <ComplianceExplorer organizationId={selectedOrgId} />;
}
