import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "@/api/client";
import { clearAccessToken, getAccessToken, setAccessToken } from "@/auth/token";
import type { Organization, UserOut } from "@/api/types";

type AuthState = {
  user: UserOut | null;
  organizations: Organization[];
  selectedOrgId: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  setSelectedOrgId: (id: string) => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setOrganizations([]);
      setSelectedOrgId(null);
      return;
    }
    const me = await api.me();
    setUser(me);
    const orgs = await api.organizations();
    setOrganizations(orgs);
    setSelectedOrgId((prev) => {
      if (prev && orgs.some((o) => o.id === prev)) return prev;
      if (me.org_memberships.length > 0) return me.org_memberships[0].organization_id;
      return orgs[0]?.id ?? null;
    });
  }, []);

  useEffect(() => {
    refresh()
      .catch(() => clearAccessToken())
      .finally(() => setLoading(false));
  }, [refresh]);

  const login = useCallback(
    async (username: string, password: string) => {
      const res = await api.login(username, password);
      setAccessToken(res.access_token);
      await refresh();
    },
    [refresh],
  );

  const logout = useCallback(() => {
    clearAccessToken();
    setUser(null);
    setOrganizations([]);
    setSelectedOrgId(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      organizations,
      selectedOrgId,
      loading,
      login,
      logout,
      setSelectedOrgId,
      refresh,
    }),
    [user, organizations, selectedOrgId, loading, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
