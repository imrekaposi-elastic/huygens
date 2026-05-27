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
