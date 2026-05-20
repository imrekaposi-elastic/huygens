export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export type OrgMembership = {
  organization_id: string;
  roles: string[];
};

export type UserOut = {
  id: string;
  email: string;
  username: string;
  platform_roles: string[];
  org_memberships: OrgMembership[];
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
};

export type AgentTechnology = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  platform_enabled: boolean;
};

export type InfrastructureProvider = {
  id: string;
  name: string;
  slug: string;
  operational: boolean;
  total_agents: number;
};

export type InfrastructureProviderDetail = InfrastructureProvider & {
  region_tree: RegionTreeNode[];
};

export type AgentOnRegion = {
  id: string;
  name: string;
  base_url: string;
  agent_technology_id: string;
  agent_technology_slug: string;
  connection_status: string;
};

export type RegionTreeNode = {
  id: string;
  infrastructure_provider_id: string;
  parent_region_id: string | null;
  name: string;
  slug: string;
  has_direct_agent: boolean;
  operational: boolean;
  descendant_agent_count: number;
  agents: AgentOnRegion[];
  children: RegionTreeNode[];
};

export type VmInventoryItem = {
  name: string | null;
  state: string | null;
  libvirt_state: string | null;
  guest_status: string | null;
  memory_mib: number | null;
  ips: string[];
  networks: string[];
  orphaned: boolean;
  project_id: string | null;
  project_name: string | null;
  project_slug: string | null;
};

export type NetworkInventoryItem = {
  name: string | null;
  active: boolean | null;
  readonly: boolean | null;
  bridge: string | null;
  orphaned: boolean;
  project_id: string | null;
  project_name: string | null;
  project_slug: string | null;
};

export type AgentInventorySummary = {
  agent_id: string;
  agent_name: string | null;
  organization_id: string;
  region_id: string;
  polled_at: string | null;
  config_drift: boolean;
  poll_error: string | null;
  vm_count: number;
  network_count: number;
  connection_status: string | null;
  vms: VmInventoryItem[];
  networks: NetworkInventoryItem[];
  orphaned_vm_count: number;
  orphaned_network_count: number;
};

export type OrganizationDashboard = {
  organization_id: string;
  agent_count: number;
  vm_count: number;
  network_count: number;
  agents_with_drift: number;
  agents_with_errors: number;
  agents: AgentInventorySummary[];
};

export type Project = {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description: string | null;
};

export type ProjectAgentTechnology = {
  agent_technology_id: string;
  slug: string;
  name: string;
  description: string | null;
  platform_enabled: boolean;
  enabled: boolean;
};

export type AgentSummary = {
  id: string;
  name: string;
  base_url: string;
  organization_id: string;
  agent_technology_id: string;
  agent_technology_slug: string;
  connection_status: string;
};

export type AgentOut = {
  id: string;
  name: string;
  organization_id: string;
  infrastructure_provider_id: string;
  region_id: string;
  agent_technology_id: string;
  agent_technology_slug: string;
  base_url: string;
  connection_status: string;
  last_poll_error?: string | null;
  last_seen_at?: string | null;
  tls_verify?: boolean;
};

export type AgentCreated = AgentOut & {
  agent_token: string;
};

export type InventoryCloudEvent = {
  type: string;
  data: {
    agent_id: string;
    organization_id: string;
    vms: { name: string; state: string }[];
    networks: { name: string; readonly?: boolean }[];
    polled_at: string;
  };
};
