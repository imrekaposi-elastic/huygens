import type { Organization } from "@/api/types";
import { getAccessToken, isPlatformAdmin } from "@/auth/token";

/** Platform admin with no organizations yet — show first-run setup wizard. */
export function needsPlatformSetup(organizations: Organization[]): boolean {
  return isPlatformAdmin(getAccessToken()) && organizations.length === 0;
}

export function slugFromName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .replace(/-+/g, "-")
    .slice(0, 64);
}

export function isValidOrgSlug(slug: string): boolean {
  return /^[a-z0-9][a-z0-9-]*$/.test(slug);
}
