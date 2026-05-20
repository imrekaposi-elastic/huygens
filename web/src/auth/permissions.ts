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
