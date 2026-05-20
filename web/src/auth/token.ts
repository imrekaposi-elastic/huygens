/** JWT storage — memory first; sessionStorage for reload only (never URL query). */

let memoryToken: string | null = null;

const STORAGE_KEY = "huy_access_token";

export function getAccessToken(): string | null {
  if (memoryToken) return memoryToken;
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAccessToken(token: string): void {
  memoryToken = token;
  try {
    sessionStorage.setItem(STORAGE_KEY, token);
  } catch {
    /* private mode */
  }
}

export function clearAccessToken(): void {
  memoryToken = null;
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

/** Parse OIDC fragment (#access_token=…) — never use query string. */
export function parseTokenFromHash(hash: string): string | null {
  if (!hash.startsWith("#")) return null;
  const params = new URLSearchParams(hash.slice(1));
  const forbidden = ["token", "access_token", "jwt"];
  for (const key of forbidden) {
    if (params.has(key) && window.location.search.includes(`${key}=`)) {
      console.error("Refusing query-string token; use OIDC fragment only");
      return null;
    }
  }
  return params.get("access_token");
}

export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const parts = token.split(".");
  if (parts.length < 2) return null;
  try {
    const json = atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function isPlatformAdmin(token: string | null): boolean {
  if (!token) return false;
  const payload = decodeJwtPayload(token);
  const roles = payload?.platform_roles;
  return Array.isArray(roles) && roles.includes("platform_admin");
}
