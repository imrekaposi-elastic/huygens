import type { UserOut } from "@/api/types";

export function isPlatformAdmin(user: UserOut | null | undefined): boolean {
  return !!user?.platform_roles.includes("platform_admin");
}

export function isOrgAdmin(user: UserOut | null | undefined, organizationId: string): boolean {
  if (!user) return false;
  if (isPlatformAdmin(user)) return true;
  const membership = user.org_memberships.find((m) => m.organization_id === organizationId);
  return membership?.roles.includes("admin") ?? false;
}

export function canManageOrgIpam(user: UserOut | null | undefined, organizationId: string): boolean {
  return isOrgAdmin(user, organizationId);
}
