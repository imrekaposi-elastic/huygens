import { clearAccessToken, getAccessToken } from "@/auth/token";
import type {
  AgentInventorySummary,
  AgentOut,
  AgentSummary,
  Organization,
  OrganizationDashboard,
  Project,
  TokenResponse,
  UserOut,
} from "@/api/types";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, { ...init, headers });
  if (res.status === 401) {
    clearAccessToken();
    window.location.href = "/login";
    throw new ApiError("Unauthorized", 401);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* non-json */
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  login: (username: string, password: string) =>
    request<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  me: () => request<UserOut>("/api/v1/auth/me"),

  organizations: () => request<Organization[]>("/api/v1/organizations"),

  dashboard: (orgId: string) =>
    request<OrganizationDashboard>(`/api/v1/inventory/organizations/${orgId}/dashboard`),

  inventoryAgents: () => request<AgentInventorySummary[]>("/api/v1/inventory/agents"),

  projects: (orgId?: string) =>
    request<Project[]>(
      orgId ? `/api/v1/projects?organization_id=${encodeURIComponent(orgId)}` : "/api/v1/projects",
    ),

  createProject: (body: {
    organization_id: string;
    name: string;
    slug: string;
    description?: string;
  }) =>
    request<Project>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  projectAgents: (projectId: string) =>
    request<AgentSummary[]>(`/api/v1/projects/${projectId}/agents`),

  registryAgents: () => request<AgentOut[]>("/api/v1/agents"),

  listVms: (projectId: string, agentId: string) =>
    request<Record<string, unknown>[]>(
      `/api/v1/projects/${projectId}/agents/${agentId}/vms`,
    ),

  listNetworks: (projectId: string, agentId: string) =>
    request<Record<string, unknown>[]>(
      `/api/v1/projects/${projectId}/agents/${agentId}/networks`,
    ),

  createVm: (projectId: string, agentId: string, body: Record<string, unknown>) =>
    request<Record<string, unknown>>(
      `/api/v1/projects/${projectId}/agents/${agentId}/vms`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  deleteVm: (projectId: string, agentId: string, name: string) =>
    request<void>(
      `/api/v1/projects/${projectId}/agents/${agentId}/vms/${encodeURIComponent(name)}`,
      { method: "DELETE" },
    ),

  createNetwork: (projectId: string, agentId: string, body: Record<string, unknown>) =>
    request<Record<string, unknown>>(
      `/api/v1/projects/${projectId}/agents/${agentId}/networks`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  deleteNetwork: (projectId: string, agentId: string, name: string) =>
    request<void>(
      `/api/v1/projects/${projectId}/agents/${agentId}/networks/${encodeURIComponent(name)}`,
      { method: "DELETE" },
    ),
};
