import type { UserOut } from "@/api/types";

export function canManageOrgUsers(
  user: UserOut | null,
  organizationId: string | null,
  platformAdmin: boolean,
): boolean {
  if (!user || !organizationId) return false;
  if (platformAdmin) return true;
  const membership = user.org_memberships.find((m) => m.organization_id === organizationId);
  return membership?.roles.includes("admin") ?? false;
}

export function canAccessAdmin(
  user: UserOut | null,
  organizationId: string | null,
  platformAdmin: boolean,
): boolean {
  return canManageOrgUsers(user, organizationId, platformAdmin);
}

/** Org-level IPAM: platform admin or organization admin. */
export function canAccessIpam(
  user: UserOut | null,
  organizationId: string | null,
  platformAdmin: boolean,
): boolean {
  return canManageOrgUsers(user, organizationId, platformAdmin);
}

const COMPLIANCE_ORG_ROLES = new Set([
  "admin",
  "compliance_admin",
  "compliance_engineer",
  "compliance_reader",
]);

/** Org compliance catalog, dashboard, placement rationale. */
export function canAccessCompliance(
  user: UserOut | null,
  organizationId: string | null,
  platformAdmin: boolean,
): boolean {
  if (!user || !organizationId) return false;
  if (platformAdmin) return true;
  const membership = user.org_memberships.find((m) => m.organization_id === organizationId);
  if (!membership) return false;
  return membership.roles.some((r) => COMPLIANCE_ORG_ROLES.has(r));
}

/** Infrastructure provider/region compliance (same roles as catalog manage). */
export function canManageInfrastructureCompliance(
  user: UserOut | null,
  organizationId: string | null,
  platformAdmin: boolean,
): boolean {
  return canManageComplianceCatalog(user, organizationId, platformAdmin);
}

export function canManageComplianceCatalog(
  user: UserOut | null,
  organizationId: string | null,
  platformAdmin: boolean,
): boolean {
  if (!user || !organizationId) return false;
  if (platformAdmin) return true;
  const membership = user.org_memberships.find((m) => m.organization_id === organizationId);
  if (!membership) return false;
  return membership.roles.includes("admin") || membership.roles.includes("compliance_admin");
}

export function canAssignComplianceCriticality(
  user: UserOut | null,
  organizationId: string | null,
  platformAdmin: boolean,
): boolean {
  if (!user || !organizationId) return false;
  if (platformAdmin) return true;
  const membership = user.org_memberships.find((m) => m.organization_id === organizationId);
  if (!membership) return false;
  return (
    membership.roles.includes("admin") || membership.roles.includes("compliance_engineer")
  );
}

/** SSH session list/connect or policy admin. */
export function canAccessSsh(
  user: UserOut | null,
  organizationId: string | null,
  platformAdmin: boolean,
): boolean {
  if (!user) return false;
  if (platformAdmin) return true;
  if (!organizationId) return false;
  if (user.org_memberships.some((m) => m.organization_id === organizationId && m.roles.includes("admin"))) {
    return true;
  }
  return user.project_roles.some(
    (g) =>
      g.organization_id === organizationId &&
      ["ssh_access", "project_admin", "security_engineer", "auditor"].includes(g.role),
  );
}

/** Topology view: any org member or project grant in the org. */
export function canAccessTopology(
  user: UserOut | null,
  organizationId: string | null,
  platformAdmin: boolean,
): boolean {
  if (!user || !organizationId) return false;
  if (platformAdmin) return true;
  if (user.org_memberships.some((m) => m.organization_id === organizationId)) return true;
  return user.project_roles.some((g) => g.organization_id === organizationId);
}
