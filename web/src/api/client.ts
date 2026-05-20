import { clearAccessToken, getAccessToken } from "@/auth/token";
import type {
  AgentCreated,
  AgentInventorySummary,
  AgentOut,
  AgentSummary,
  AgentTechnology,
  InfrastructureProvider,
  HostMetricsSnapshot,
  InfrastructureProviderDetail,
  IpAllocation,
  IpPool,
  Organization,
  OrganizationDashboard,
  Project,
  ProjectAgentTechnology,
  RegionTreeNode,
  WizardPlanResponse,
  IdpGroupMapping,
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

  createOrganization: (body: { name: string; slug: string }) =>
    request<Organization>("/api/v1/organizations", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteOrganization: (organizationId: string) =>
    request<void>(`/api/v1/organizations/${encodeURIComponent(organizationId)}`, {
      method: "DELETE",
    }),

  orgUsers: (organizationId: string) =>
    request<UserOut[]>(`/api/v1/organizations/${encodeURIComponent(organizationId)}/users`),

  createOrgUser: (
    organizationId: string,
    body: {
      email: string;
      username: string;
      password: string;
      display_name?: string;
      org_roles?: string[];
    },
  ) =>
    request<UserOut>(`/api/v1/organizations/${encodeURIComponent(organizationId)}/users`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateOrgUserRoles: (organizationId: string, userId: string, org_roles: string[]) =>
    request<UserOut>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/users/${encodeURIComponent(userId)}/roles`,
      { method: "PUT", body: JSON.stringify({ org_roles }) },
    ),

  assignProjectRole: (
    organizationId: string,
    userId: string,
    body: { project_id: string; role: string },
  ) =>
    request<{ status: string; project_id: string; role: string }>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/users/${encodeURIComponent(userId)}/project-roles`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  revokeProjectRole: (
    organizationId: string,
    userId: string,
    projectId: string,
    role: string,
  ) =>
    request<void>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/users/${encodeURIComponent(userId)}/project-roles?project_id=${encodeURIComponent(projectId)}&role=${encodeURIComponent(role)}`,
      { method: "DELETE" },
    ),

  grantPlatformAdmin: (userId: string) =>
    request<UserOut>(`/api/v1/users/${encodeURIComponent(userId)}/platform-roles`, {
      method: "POST",
      body: JSON.stringify({ role: "platform_admin" }),
    }),

  orgIdpMappings: (organizationId: string) =>
    request<IdpGroupMapping[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/idp-group-mappings`,
    ),

  createOrgIdpMapping: (
    organizationId: string,
    body: {
      idp_group_name: string;
      match_type?: string;
      huy_role: string;
      priority?: number;
      enabled?: boolean;
    },
  ) =>
    request<IdpGroupMapping>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/idp-group-mappings`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  patchOrgIdpMapping: (
    organizationId: string,
    mappingId: string,
    body: Partial<{
      idp_group_name: string;
      match_type: string;
      huy_role: string;
      priority: number;
      enabled: boolean;
    }>,
  ) =>
    request<IdpGroupMapping>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/idp-group-mappings/${encodeURIComponent(mappingId)}`,
      { method: "PATCH", body: JSON.stringify(body) },
    ),

  deleteOrgIdpMapping: (organizationId: string, mappingId: string) =>
    request<void>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/idp-group-mappings/${encodeURIComponent(mappingId)}`,
      { method: "DELETE" },
    ),

  platformIdpMappings: () =>
    request<IdpGroupMapping[]>("/api/v1/platform/idp-group-mappings"),

  createPlatformIdpMapping: (body: {
    idp_group_name: string;
    match_type?: string;
    huy_role: string;
    priority?: number;
    enabled?: boolean;
  }) =>
    request<IdpGroupMapping>("/api/v1/platform/idp-group-mappings", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  patchPlatformIdpMapping: (
    mappingId: string,
    body: Partial<{
      idp_group_name: string;
      match_type: string;
      huy_role: string;
      priority: number;
      enabled: boolean;
    }>,
  ) =>
    request<IdpGroupMapping>(
      `/api/v1/platform/idp-group-mappings/${encodeURIComponent(mappingId)}`,
      { method: "PATCH", body: JSON.stringify(body) },
    ),

  deletePlatformIdpMapping: (mappingId: string) =>
    request<void>(`/api/v1/platform/idp-group-mappings/${encodeURIComponent(mappingId)}`, {
      method: "DELETE",
    }),

  oidcAuthorizeUrl: (organizationId: string) =>
    request<{ authorization_url: string }>(
      `/api/v1/auth/oidc/authorize?organization_id=${encodeURIComponent(organizationId)}`,
    ),

  dashboard: (orgId: string) =>
    request<OrganizationDashboard>(`/api/v1/inventory/organizations/${orgId}/dashboard`),

  inventoryAgents: () => request<AgentInventorySummary[]>("/api/v1/inventory/agents"),

  projects: (orgId?: string) =>
    request<Project[]>(
      orgId ? `/api/v1/projects?organization_id=${encodeURIComponent(orgId)}` : "/api/v1/projects",
    ),

  getProject: (projectId: string) =>
    request<Project>(`/api/v1/projects/${encodeURIComponent(projectId)}`),

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

  deleteProject: (projectId: string) =>
    request<void>(`/api/v1/projects/${encodeURIComponent(projectId)}`, {
      method: "DELETE",
    }),

  listIpamPools: (organizationId: string) =>
    request<IpPool[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/ipam/pools`,
    ),

  listPoolAllocations: (organizationId: string, poolId: string) =>
    request<IpAllocation[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/ipam/pools/${encodeURIComponent(poolId)}/allocations`,
    ),

  createIpamPool: (
    organizationId: string,
    body: { name: string; cidr: string; description?: string; exceptions?: string[] },
  ) =>
    request<IpPool>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/ipam/pools`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  ipamWizardPlan: (
    organizationId: string,
    body: {
      pool_id: string;
      network_count: number;
      hosts_per_network: number;
      exceptions?: string[];
    },
  ) =>
    request<WizardPlanResponse>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/ipam/wizard/plan`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  ipamWizardApply: (
    organizationId: string,
    projectId: string,
    body: { pool_id: string; subnets: { cidr: string; name?: string }[] },
  ) =>
    request<IpAllocation[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/ipam/projects/${encodeURIComponent(projectId)}/wizard/apply`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  listProjectIpAllocations: (organizationId: string, projectId: string) =>
    request<IpAllocation[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/ipam/projects/${encodeURIComponent(projectId)}/allocations`,
    ),

  projectAgentTechnologies: (projectId: string) =>
    request<ProjectAgentTechnology[]>(
      `/api/v1/projects/${encodeURIComponent(projectId)}/agent-technologies`,
    ),

  setProjectAgentTechnologies: (
    projectId: string,
    technologies: { agent_technology_id: string; enabled: boolean }[],
  ) =>
    request<ProjectAgentTechnology[]>(
      `/api/v1/projects/${encodeURIComponent(projectId)}/agent-technologies`,
      {
        method: "PUT",
        body: JSON.stringify({ technologies }),
      },
    ),

  projectAgents: (projectId: string) =>
    request<AgentSummary[]>(`/api/v1/projects/${projectId}/agents`),

  agentTechnologies: () => request<AgentTechnology[]>("/api/v1/agent-technologies"),

  updateAgentTechnology: (
    technologyId: string,
    body: { platform_enabled?: boolean; name?: string; description?: string },
  ) =>
    request<AgentTechnology>(`/api/v1/agent-technologies/${encodeURIComponent(technologyId)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  infrastructureProviders: () =>
    request<InfrastructureProvider[]>("/api/v1/infrastructure-providers"),

  infrastructureProvider: (id: string) =>
    request<InfrastructureProviderDetail>(
      `/api/v1/infrastructure-providers/${encodeURIComponent(id)}`,
    ),

  createInfrastructureProvider: (body: { name: string; slug: string }) =>
    request<InfrastructureProvider>("/api/v1/infrastructure-providers", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  deleteInfrastructureProvider: (id: string) =>
    request<void>(`/api/v1/infrastructure-providers/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),

  regionTree: (infrastructureProviderId: string) =>
    request<RegionTreeNode[]>(
      `/api/v1/infrastructure-providers/${encodeURIComponent(infrastructureProviderId)}/region-tree`,
    ),

  createRegion: (
    infrastructureProviderId: string,
    body: { name: string; slug: string; parent_region_id?: string | null },
  ) =>
    request<{ id: string }>(
      `/api/v1/infrastructure-providers/${encodeURIComponent(infrastructureProviderId)}/regions`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  deleteRegion: (infrastructureProviderId: string, regionId: string) =>
    request<void>(
      `/api/v1/infrastructure-providers/${encodeURIComponent(infrastructureProviderId)}/regions/${encodeURIComponent(regionId)}`,
      { method: "DELETE" },
    ),

  registryAgents: () => request<AgentOut[]>("/api/v1/agents"),

  registerAgent: (body: {
    name: string;
    base_url: string;
    organization_id: string;
    infrastructure_provider_id: string;
    region_id: string;
    agent_technology_id: string;
    tls_verify?: boolean;
  }) =>
    request<AgentCreated>("/api/v1/agents", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  testAgentConnection: (agentId: string) =>
    request<AgentOut>(`/api/v1/agents/${encodeURIComponent(agentId)}/test-connection`, {
      method: "POST",
    }),

  agentMetrics: (agentId: string) =>
    request<HostMetricsSnapshot>(`/api/v1/agents/${encodeURIComponent(agentId)}/metrics`),

  patchAgent: (
    agentId: string,
    body: {
      tls_verify?: boolean;
      base_url?: string;
      region_id?: string;
      infrastructure_provider_id?: string;
    },
  ) =>
    request<AgentOut>(`/api/v1/agents/${encodeURIComponent(agentId)}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  deleteAgent: (agentId: string) =>
    request<void>(`/api/v1/agents/${encodeURIComponent(agentId)}`, {
      method: "DELETE",
    }),

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

  patchVm: (projectId: string, agentId: string, name: string, body: Record<string, unknown>) =>
    request<Record<string, unknown>>(
      `/api/v1/projects/${projectId}/agents/${agentId}/vms/${encodeURIComponent(name)}`,
      { method: "PATCH", body: JSON.stringify(body) },
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

  patchNetwork: (
    projectId: string,
    agentId: string,
    name: string,
    body: Record<string, unknown>,
  ) =>
    request<Record<string, unknown>>(
      `/api/v1/projects/${projectId}/agents/${agentId}/networks/${encodeURIComponent(name)}`,
      { method: "PATCH", body: JSON.stringify(body) },
    ),

  deleteNetwork: (projectId: string, agentId: string, name: string) =>
    request<void>(
      `/api/v1/projects/${projectId}/agents/${agentId}/networks/${encodeURIComponent(name)}`,
      { method: "DELETE" },
    ),

  assignResourceToProject: (
    projectId: string,
    agentId: string,
    body: { resource_type: "vm" | "network"; name: string },
  ) =>
    request<{
      agent_id: string;
      resource_type: string;
      name: string;
      project_id: string;
      project_name: string;
      project_slug: string;
    }>(`/api/v1/projects/${projectId}/agents/${agentId}/assignments`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  unassignResourceFromProject: (
    projectId: string,
    agentId: string,
    resourceType: "vm" | "network",
    name: string,
  ) =>
    request<void>(
      `/api/v1/projects/${projectId}/agents/${agentId}/assignments/${resourceType}/${encodeURIComponent(name)}`,
      { method: "DELETE" },
    ),

  listCloudInitProfiles: (projectId: string, agentId: string) =>
    request<Record<string, unknown>[]>(
      `/api/v1/projects/${projectId}/agents/${agentId}/cloud-init`,
    ),

  getCloudInitProfile: (projectId: string, agentId: string, name: string) =>
    request<Record<string, unknown>>(
      `/api/v1/projects/${projectId}/agents/${agentId}/cloud-init/${encodeURIComponent(name)}`,
    ),

  createCloudInitProfile: (
    projectId: string,
    agentId: string,
    body: {
      name: string;
      user_data: string;
      meta_data?: string;
      network_config?: string | null;
      ssh_keys?: string[];
    },
  ) =>
    request<Record<string, unknown>>(
      `/api/v1/projects/${projectId}/agents/${agentId}/cloud-init`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  updateCloudInitProfile: (
    projectId: string,
    agentId: string,
    name: string,
    body: {
      user_data?: string;
      meta_data?: string;
      network_config?: string | null;
      ssh_keys?: string[];
    },
  ) =>
    request<Record<string, unknown>>(
      `/api/v1/projects/${projectId}/agents/${agentId}/cloud-init/${encodeURIComponent(name)}`,
      { method: "PATCH", body: JSON.stringify(body) },
    ),

  validateCloudInit: (
    projectId: string,
    agentId: string,
    body: {
      user_data: string;
      meta_data?: string;
      network_config?: string | null;
      ssh_keys?: string[];
    },
  ) =>
    request<{ valid: boolean; message: string; mode?: string }>(
      `/api/v1/projects/${projectId}/agents/${agentId}/cloud-init/validate`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  deleteCloudInitProfile: (projectId: string, agentId: string, name: string) =>
    request<void>(
      `/api/v1/projects/${projectId}/agents/${agentId}/cloud-init/${encodeURIComponent(name)}`,
      { method: "DELETE" },
    ),

  deleteOrgUser: (organizationId: string, userId: string) =>
    request<void>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/users/${encodeURIComponent(userId)}`,
      { method: "DELETE" },
    ),

  listImages: (projectId: string, agentId: string) =>
    request<Record<string, unknown>[]>(
      `/api/v1/projects/${projectId}/agents/${agentId}/images`,
    ),

  createImage: (
    projectId: string,
    agentId: string,
    body: { name: string; source: string; sha256?: string; fetch?: boolean },
  ) =>
    request<Record<string, unknown>>(
      `/api/v1/projects/${projectId}/agents/${agentId}/images`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  deleteImage: (projectId: string, agentId: string, name: string) =>
    request<void>(
      `/api/v1/projects/${projectId}/agents/${agentId}/images/${encodeURIComponent(name)}`,
      { method: "DELETE" },
    ),
};
