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
  AssetCriticality,
  ComplianceCheck,
  ComplianceDashboard,
  ComplianceExplorerFacets,
  ComplianceExplorerResult,
  ComplianceExplorerSuggestResult,
  ComplianceItem,
  InfrastructureProviderCompliance,
  RegionCompliance,
  FlatBreakoutConfig,
  IdpGroupMapping,
  PlacementRationale,
  MoscowKind,
  NetworkBreakout,
  ComplianceStandard,
  ComplianceControl,
  ComplianceCycle,
  ControlEvidence,
  CompliancePack,
  ComplianceExportJob,
  QualitativeCharacteristic,
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

function filenameFromContentDisposition(header: string | null): string | null {
  if (!header) return null;
  const m = /filename="([^"]+)"/.exec(header);
  return m?.[1] ?? null;
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
    body: {
      name: string;
      cidr: string;
      description?: string;
      exceptions?: string[];
      pool_kind?: "vnet" | "overlay";
    },
  ) =>
    request<IpPool>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/ipam/pools`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  deleteIpamPool: (organizationId: string, poolId: string) =>
    request<void>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/ipam/pools/${encodeURIComponent(poolId)}`,
      { method: "DELETE" },
    ),

  topology: (organizationId: string) =>
    request<import("@/api/types").Topology>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/topology`,
    ),

  listNetworkLinks: (organizationId: string) =>
    request<import("@/api/types").NetworkLink[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/network-links`,
    ),

  getNetworkLink: (organizationId: string, linkId: string) =>
    request<import("@/api/types").NetworkLink>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/network-links/${encodeURIComponent(linkId)}`,
    ),

  createNetworkLink: (
    organizationId: string,
    body: {
      overlay_pool_id?: string;
      name?: string;
      left: import("@/api/types").NetworkLinkEndpoint;
      right: import("@/api/types").NetworkLinkEndpoint;
    },
  ) =>
    request<import("@/api/types").NetworkLink>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/network-links`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  deleteNetworkLink: (organizationId: string, linkId: string) =>
    request<import("@/api/types").NetworkLink>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/network-links/${encodeURIComponent(linkId)}`,
      { method: "DELETE" },
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

  getNetworkBreakout: (projectId: string, agentId: string, name: string) =>
    request<NetworkBreakout>(
      `/api/v1/projects/${projectId}/agents/${agentId}/networks/${encodeURIComponent(name)}/breakout`,
    ),

  putFlatBreakout: (
    projectId: string,
    agentId: string,
    name: string,
    body: FlatBreakoutConfig,
  ) =>
    request<NetworkBreakout>(
      `/api/v1/projects/${projectId}/agents/${agentId}/networks/${encodeURIComponent(name)}/breakout/flat`,
      { method: "PUT", body: JSON.stringify(body) },
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

  complianceDashboard: (organizationId: string) =>
    request<ComplianceDashboard>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-dashboard`,
    ),

  complianceExplorerFacets: (organizationId: string) =>
    request<ComplianceExplorerFacets>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-explorer/facets`,
    ),

  complianceExplorerSuggest: (
    organizationId: string,
    params: { q: string; resource_type?: "project" | "vm" | "network"; limit?: number },
  ) => {
    const qs = new URLSearchParams({ q: params.q });
    if (params.resource_type) qs.set("resource_type", params.resource_type);
    if (params.limit != null) qs.set("limit", String(params.limit));
    return request<ComplianceExplorerSuggestResult>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-explorer/suggest?${qs}`,
    );
  },

  complianceExplorer: (
    organizationId: string,
    params: {
      catalog_slug?: string;
      catalog_item_id?: string;
      catalog_match?: "has" | "missing";
      trait_key?: string;
      trait_match?: "has" | "missing";
      trait_scope?: "any" | "provider" | "region";
      resource_type?: "project" | "vm" | "network";
      q?: string;
      resource_key?: string;
      offset?: number;
      page_size?: number;
    },
  ) => {
    const q = new URLSearchParams();
    if (params.catalog_slug) q.set("catalog_slug", params.catalog_slug);
    if (params.catalog_item_id) q.set("catalog_item_id", params.catalog_item_id);
    if (params.catalog_match) q.set("catalog_match", params.catalog_match);
    if (params.trait_key) q.set("trait_key", params.trait_key);
    if (params.trait_match) q.set("trait_match", params.trait_match);
    if (params.trait_scope) q.set("trait_scope", params.trait_scope);
    if (params.resource_type) q.set("resource_type", params.resource_type);
    if (params.q) q.set("q", params.q);
    if (params.resource_key) q.set("resource_key", params.resource_key);
    if (params.offset != null) q.set("offset", String(params.offset));
    if (params.page_size != null) q.set("page_size", String(params.page_size));
    const qs = q.toString();
    return request<ComplianceExplorerResult>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-explorer${qs ? `?${qs}` : ""}`,
    );
  },

  listComplianceCatalog: (organizationId: string) =>
    request<ComplianceItem[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-catalog`,
    ),

  createComplianceCatalogItem: (
    organizationId: string,
    body: {
      name: string;
      slug?: string;
      description?: string;
      reference_url?: string;
      moscow?: MoscowKind;
      target_level?: string;
    },
  ) =>
    request<ComplianceItem>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-catalog`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  updateComplianceCatalogItem: (
    organizationId: string,
    itemId: string,
    body: {
      name?: string;
      description?: string | null;
      reference_url?: string | null;
      moscow?: MoscowKind;
      target_level?: string | null;
    },
  ) =>
    request<ComplianceItem>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-catalog/${encodeURIComponent(itemId)}`,
      { method: "PATCH", body: JSON.stringify(body) },
    ),

  deleteComplianceCatalogItem: (organizationId: string, itemId: string) =>
    request<void>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-catalog/${encodeURIComponent(itemId)}`,
      { method: "DELETE" },
    ),

  listComplianceChecks: (organizationId: string) =>
    request<ComplianceCheck[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-checks`,
    ),

  createComplianceCheck: (
    organizationId: string,
    body: {
      compliance_item_id: string;
      owner_user_id: string;
      owner_display?: string;
      valid_until: string;
      status?: "active" | "expired" | "waived";
    },
  ) =>
    request<ComplianceCheck>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-checks`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  updateComplianceCheck: (
    organizationId: string,
    checkId: string,
    body: {
      owner_user_id?: string;
      owner_display?: string;
      valid_until?: string;
      status?: "active" | "expired" | "waived";
    },
  ) =>
    request<ComplianceCheck>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-checks/${encodeURIComponent(checkId)}`,
      { method: "PATCH", body: JSON.stringify(body) },
    ),

  deleteComplianceCheck: (organizationId: string, checkId: string) =>
    request<void>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-checks/${encodeURIComponent(checkId)}`,
      { method: "DELETE" },
    ),

  getProviderComplianceProfile: (organizationId: string, providerId: string) =>
    request<InfrastructureProviderCompliance>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/infrastructure-providers/${encodeURIComponent(providerId)}/compliance-profile`,
    ),

  setProviderComplianceProfile: (
    organizationId: string,
    providerId: string,
    body: { compliance_item_ids: string[]; is_compliant?: boolean },
  ) =>
    request<InfrastructureProviderCompliance>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/infrastructure-providers/${encodeURIComponent(providerId)}/compliance-profile`,
      { method: "PUT", body: JSON.stringify(body) },
    ),

  getRegionComplianceItems: (organizationId: string, regionId: string) =>
    request<RegionCompliance>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/regions/${encodeURIComponent(regionId)}/compliance-items`,
    ),

  setRegionComplianceItems: (
    organizationId: string,
    regionId: string,
    body: { compliance_item_ids: string[] },
  ) =>
    request<RegionCompliance>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/regions/${encodeURIComponent(regionId)}/compliance-items`,
      { method: "PUT", body: JSON.stringify(body) },
    ),

  placementRationale: (
    organizationId: string,
    params: {
      resource_type: "project" | "vm" | "network";
      project_id: string;
      agent_id?: string;
      name?: string;
    },
  ) => {
    const q = new URLSearchParams({ project_id: params.project_id });
    if (params.agent_id) q.set("agent_id", params.agent_id);
    if (params.name) q.set("name", params.name);
    return request<PlacementRationale>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/resources/${encodeURIComponent(params.resource_type)}/placement-rationale?${q}`,
    );
  },

  getProjectCriticality: (organizationId: string, projectId: string) =>
    request<AssetCriticality>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/projects/${encodeURIComponent(projectId)}/criticality`,
    ),

  setProjectCriticality: (
    organizationId: string,
    projectId: string,
    body: { compliance_item_ids: string[]; placement_note?: string },
  ) =>
    request<AssetCriticality>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/projects/${encodeURIComponent(projectId)}/criticality`,
      { method: "PUT", body: JSON.stringify(body) },
    ),

  getResourceCriticality: (
    organizationId: string,
    projectId: string,
    resourceType: "vm" | "network",
    name: string,
    agentId: string,
  ) => {
    const q = new URLSearchParams({ agent_id: agentId });
    return request<AssetCriticality>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/projects/${encodeURIComponent(projectId)}/resources/${encodeURIComponent(resourceType)}/${encodeURIComponent(name)}/criticality?${q}`,
    );
  },

  setResourceCriticality: (
    organizationId: string,
    projectId: string,
    resourceType: "vm" | "network",
    name: string,
    agentId: string,
    body: { compliance_item_ids: string[]; placement_note?: string },
  ) => {
    const q = new URLSearchParams({ agent_id: agentId });
    return request<AssetCriticality>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/projects/${encodeURIComponent(projectId)}/resources/${encodeURIComponent(resourceType)}/${encodeURIComponent(name)}/criticality?${q}`,
      { method: "PUT", body: JSON.stringify(body) },
    );
  },

  // ---- Phase 7+ GRC APIs (huy-compliance) ----
  listComplianceStandards: (organizationId: string) =>
    request<ComplianceStandard[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-standards`,
    ),

  createComplianceStandard: (
    organizationId: string,
    body: {
      name: string;
      slug?: string;
      description?: string | null;
      reference_url?: string | null;
      moscow?: MoscowKind;
      target_level?: string | null;
    },
  ) =>
    request<ComplianceStandard>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-standards`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  updateComplianceStandard: (
    organizationId: string,
    standardId: string,
    body: {
      name?: string;
      description?: string | null;
      reference_url?: string | null;
      moscow?: MoscowKind;
      target_level?: string | null;
    },
  ) =>
    request<ComplianceStandard>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-standards/${encodeURIComponent(standardId)}`,
      { method: "PATCH", body: JSON.stringify(body) },
    ),

  deleteComplianceStandard: (organizationId: string, standardId: string) =>
    request<void>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-standards/${encodeURIComponent(standardId)}`,
      { method: "DELETE" },
    ),

  listComplianceControls: (organizationId: string, standardId: string) =>
    request<ComplianceControl[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-standards/${encodeURIComponent(standardId)}/controls`,
    ),

  createComplianceControl: (
    organizationId: string,
    standardId: string,
    body: {
      control_code?: string | null;
      name: string;
      description?: string | null;
      rationale?: string | null;
      moscow?: MoscowKind;
    },
  ) =>
    request<ComplianceControl>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-standards/${encodeURIComponent(standardId)}/controls`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  updateComplianceControl: (
    organizationId: string,
    controlId: string,
    body: {
      control_code?: string | null;
      name?: string;
      description?: string | null;
      rationale?: string | null;
      moscow?: MoscowKind;
    },
  ) =>
    request<ComplianceControl>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-controls/${encodeURIComponent(controlId)}`,
      { method: "PATCH", body: JSON.stringify(body) },
    ),

  deleteComplianceControl: (organizationId: string, controlId: string) =>
    request<void>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-controls/${encodeURIComponent(controlId)}`,
      { method: "DELETE" },
    ),

  listComplianceCycles: (organizationId: string, standardId: string) =>
    request<ComplianceCycle[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-standards/${encodeURIComponent(standardId)}/cycles`,
    ),

  createComplianceCycle: (
    organizationId: string,
    standardId: string,
    body: { name: string; status?: string; starts_at?: string | null; ends_at?: string | null },
  ) =>
    request<ComplianceCycle>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-standards/${encodeURIComponent(standardId)}/cycles`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  updateComplianceCycle: (
    organizationId: string,
    cycleId: string,
    body: { name?: string; status?: string; starts_at?: string | null; ends_at?: string | null },
  ) =>
    request<ComplianceCycle>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-cycles/${encodeURIComponent(cycleId)}`,
      { method: "PATCH", body: JSON.stringify(body) },
    ),

  deleteComplianceCycle: (organizationId: string, cycleId: string) =>
    request<void>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-cycles/${encodeURIComponent(cycleId)}`,
      { method: "DELETE" },
    ),

  getComplianceCycleStatus: (organizationId: string, cycleId: string) =>
    request<import("@/api/types").ComplianceCycleStatus>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-cycles/${encodeURIComponent(cycleId)}/status`,
    ),

  listControlEvidence: (organizationId: string, controlId: string, cycleId?: string) => {
    const q = new URLSearchParams();
    if (cycleId) q.set("cycle_id", cycleId);
    // default is to hide superseded evidence server-side
    const qs = q.toString();
    return request<ControlEvidence[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-controls/${encodeURIComponent(controlId)}/evidence${qs ? `?${qs}` : ""}`,
    );
  },

  uploadControlEvidence: async (
    organizationId: string,
    controlId: string,
    body: {
      file: File;
      category: string;
      title: string;
      summary?: string | null;
      cycle_id?: string | null;
      supersedes_evidence_id?: string | null;
    },
  ) => {
    const token = getAccessToken();
    const form = new FormData();
    form.set("file", body.file);
    form.set("category", body.category);
    form.set("title", body.title);
    if (body.summary != null) form.set("summary", body.summary);
    if (body.cycle_id != null) form.set("cycle_id", body.cycle_id);
    if (body.supersedes_evidence_id != null) form.set("supersedes_evidence_id", body.supersedes_evidence_id);
    const res = await fetch(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-controls/${encodeURIComponent(controlId)}/evidence`,
      {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: form,
      },
    );
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const json = (await res.json()) as { detail?: string };
        if (json.detail) detail = json.detail;
      } catch {
        /* non-json */
      }
      throw new ApiError(detail, res.status);
    }
    return (await res.json()) as ControlEvidence;
  },

  evidenceDownloadUrl: (organizationId: string, evidenceId: string) =>
    `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-evidence/${encodeURIComponent(evidenceId)}/download`,

  downloadEvidence: async (organizationId: string, evidenceId: string) => {
    const token = getAccessToken();
    const res = await fetch(api.evidenceDownloadUrl(organizationId, evidenceId), {
      method: "GET",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
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
    const blob = await res.blob();
    const filename = filenameFromContentDisposition(res.headers.get("content-disposition"));
    return { blob, filename };
  },

  deleteEvidence: (organizationId: string, evidenceId: string) =>
    request<void>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-evidence/${encodeURIComponent(evidenceId)}`,
      { method: "DELETE" },
    ),

  listCompliancePacks: (organizationId: string) =>
    request<CompliancePack[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-packs`,
    ),

  importCompliancePack: (
    organizationId: string,
    body: { pack_key: string; name: string; vendor?: string | null; version?: string | null; payload: unknown },
  ) =>
    request<CompliancePack>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-packs/import`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  validateCompliancePack: (
    organizationId: string,
    body: { pack_key: string; name: string; vendor?: string | null; version?: string | null; payload: unknown },
  ) =>
    request<import("@/api/types").CompliancePackValidate>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-packs/validate`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  exportDownloadUrl: (organizationId: string, jobId: string) =>
    `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-export/${encodeURIComponent(jobId)}/download`,

  /** Request PDF export, poll until ready, then download once (no job list / retention). */
  exportCompliancePdf: async (
    organizationId: string,
    body: { export_type?: "pdf"; standard_id?: string | null; cycle_id?: string | null },
    options?: { pollIntervalMs?: number; timeoutMs?: number },
  ) => {
    const pollIntervalMs = options?.pollIntervalMs ?? 1500;
    const timeoutMs = options?.timeoutMs ?? 5 * 60 * 1000;
    const job = await request<ComplianceExportJob>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-export`,
      { method: "POST", body: JSON.stringify(body) },
    );
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const status = await request<ComplianceExportJob>(
        `/api/v1/organizations/${encodeURIComponent(organizationId)}/compliance-export/${encodeURIComponent(job.id)}`,
      );
      if (status.status === "completed") {
        return api.downloadComplianceExport(organizationId, job.id);
      }
      if (status.status === "failed") {
        throw new ApiError(status.error_message ?? "Export failed", 500);
      }
      await new Promise((r) => setTimeout(r, pollIntervalMs));
    }
    throw new ApiError("Export timed out", 504);
  },

  downloadComplianceExport: async (organizationId: string, jobId: string) => {
    const token = getAccessToken();
    const res = await fetch(api.exportDownloadUrl(organizationId, jobId), {
      method: "GET",
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    });
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
    const blob = await res.blob();
    const filename = filenameFromContentDisposition(res.headers.get("content-disposition"));
    return { blob, filename: filename ?? "compliance-export.pdf" };
  },

  listQualitativeCharacteristics: (organizationId: string) =>
    request<QualitativeCharacteristic[]>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/qualitative-characteristics`,
    ),

  createQualitativeCharacteristic: (
    organizationId: string,
    body: { name: string; slug?: string; description?: string | null; moscow?: MoscowKind; kind?: string },
  ) =>
    request<QualitativeCharacteristic>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/qualitative-characteristics`,
      { method: "POST", body: JSON.stringify(body) },
    ),

  updateQualitativeCharacteristic: (
    organizationId: string,
    characteristicId: string,
    body: { name?: string; description?: string | null; moscow?: MoscowKind; kind?: string },
  ) =>
    request<QualitativeCharacteristic>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/qualitative-characteristics/${encodeURIComponent(characteristicId)}`,
      { method: "PATCH", body: JSON.stringify(body) },
    ),

  migrateLegacyTraitsToCharacteristics: (organizationId: string) =>
    request<{
      provider_traits_seen: number;
      region_traits_seen: number;
      characteristics_created: number;
      provider_links_added: number;
      region_links_added: number;
    }>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/qualitative-characteristics/migrate-from-legacy-traits`,
      { method: "POST" },
    ),

  deleteQualitativeCharacteristic: (organizationId: string, characteristicId: string) =>
    request<void>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/qualitative-characteristics/${encodeURIComponent(characteristicId)}`,
      { method: "DELETE" },
    ),

  getProviderCharacteristics: (organizationId: string, providerId: string) =>
    request<{ characteristic_ids: string[] }>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/infrastructure-providers/${encodeURIComponent(providerId)}/characteristics`,
    ),

  setProviderCharacteristics: (
    organizationId: string,
    providerId: string,
    characteristic_ids: string[],
  ) =>
    request<void>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/infrastructure-providers/${encodeURIComponent(providerId)}/characteristics`,
      { method: "PUT", body: JSON.stringify({ characteristic_ids }) },
    ),

  getRegionCharacteristics: (organizationId: string, regionId: string) =>
    request<{ characteristic_ids: string[] }>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/regions/${encodeURIComponent(regionId)}/characteristics`,
    ),

  setRegionCharacteristics: (organizationId: string, regionId: string, characteristic_ids: string[]) =>
    request<void>(
      `/api/v1/organizations/${encodeURIComponent(organizationId)}/regions/${encodeURIComponent(regionId)}/characteristics`,
      { method: "PUT", body: JSON.stringify({ characteristic_ids }) },
    ),
};
