export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

export type OrgMembership = {
  organization_id: string;
  roles: string[];
};

export type ProjectRoleOut = {
  organization_id: string;
  project_id: string;
  role: string;
};

export type UserOut = {
  id: string;
  email: string;
  username: string;
  display_name: string | null;
  is_active: boolean;
  platform_roles: string[];
  org_memberships: OrgMembership[];
  project_roles: ProjectRoleOut[];
};

export type IdpGroupMapping = {
  id: string;
  organization_id: string | null;
  idp_group_name: string;
  match_type: string;
  huy_role: string;
  priority: number;
  enabled: boolean;
  created_by: string | null;
  created_at: string;
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

export type PoolKind = "vnet" | "overlay";

export type IpPool = {
  id: string;
  organization_id: string;
  name: string;
  cidr: string;
  description: string | null;
  exceptions: string[];
  pool_kind: PoolKind;
  created_at: string;
};

export type LinkStatus = "pending" | "applying" | "connected" | "error" | "deleting";

export type LinkType = "wireguard" | "local";

export type FlatBreakoutMode = "bridge_uplink" | "macvlan" | "local_peer";

export type FlatBreakoutConfig = {
  enabled: boolean;
  mode: FlatBreakoutMode;
  uplink: string;
  remote_hypervisor_cidrs: string[];
  nat_exempt_cidrs: string[];
};

export type NetworkBreakout = {
  wireguard: Record<string, unknown>;
  flat: FlatBreakoutConfig;
};

export type NetworkLinkEndpoint = {
  agent_id: string;
  project_id: string;
  network_name: string;
};

export type NetworkLink = {
  id: string;
  organization_id: string;
  name: string | null;
  status: LinkStatus;
  link_type: LinkType;
  left: NetworkLinkEndpoint;
  right: NetworkLinkEndpoint;
  overlay_pool_id: string;
  tunnel_cidr: string;
  left_tunnel_address: string;
  right_tunnel_address: string;
  left_public_key: string;
  right_public_key: string;
  left_vnet_cidr: string | null;
  right_vnet_cidr: string | null;
  config_drift: boolean;
  last_error: string | null;
  created_at: string;
  updated_at: string;
};

export type TopologyVnetNode = {
  agent_id: string;
  agent_name?: string | null;
  project_id: string;
  project_name?: string | null;
  network_name: string;
  ipv4_cidr: string | null;
};

export type TopologyLinkEdge = {
  id: string;
  name: string | null;
  status: LinkStatus;
  link_type: LinkType;
  left: NetworkLinkEndpoint;
  right: NetworkLinkEndpoint;
  left_tunnel_address: string;
  right_tunnel_address: string;
  tunnel_cidr: string;
  config_drift: boolean;
  last_error: string | null;
};

export type Topology = {
  organization_id: string;
  vnets: TopologyVnetNode[];
  links: TopologyLinkEdge[];
};

export type IpAllocation = {
  id: string;
  pool_id: string;
  project_id: string;
  cidr: string;
  network_name: string | null;
  status: "reserved" | "allocated" | "released";
  created_at: string;
};

export type WizardSubnetPlan = {
  suggested_name: string;
  cidr: string;
};

export type WizardPlanResponse = {
  pool_id: string;
  subnets: WizardSubnetPlan[];
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
  region_id: string | null;
  region_name?: string | null;
  region_slug?: string | null;
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

export type HostMetricsSnapshot = {
  collected_at: string;
  libvirt_connected: boolean;
  vms: {
    running: number;
    total: number;
    by_libvirt_state: Record<string, number>;
  };
  cpu_percent: number;
  memory: {
    total_bytes: number;
    used_bytes: number;
    available_bytes: number;
    usage_percent: number;
    allocated_to_vms_bytes: number;
  };
  disk: {
    mount: string;
    total_bytes: number;
    used_bytes: number;
    free_bytes: number;
    usage_percent: number;
  } | null;
  disk_io: {
    read_bytes_total: number;
    write_bytes_total: number;
    read_ops_total: number;
    write_ops_total: number;
  } | null;
  network: {
    bytes_sent_total: number;
    bytes_recv_total: number;
  } | null;
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

export type MoscowKind = "must" | "should" | "could" | "wont";

export type ComplianceItem = {
  id: string;
  organization_id: string;
  name: string;
  slug: string;
  description: string | null;
  reference_url: string | null;
  moscow: MoscowKind;
  target_level: string | null;
  created_at: string;
  updated_at: string;
};

export type InfrastructureProviderCompliance = {
  organization_id: string;
  infrastructure_provider_id: string;
  is_compliant: boolean;
  compliance_items: ComplianceItem[];
  updated_at: string | null;
};

export type RegionCompliance = {
  organization_id: string;
  region_id: string;
  compliance_items: ComplianceItem[];
};

export type ComplianceTrait = {
  id: string;
  organization_id: string;
  trait_key: string;
  title: string;
  description: string | null;
  moscow: MoscowKind;
  infrastructure_provider_id?: string | null;
  region_id?: string | null;
  created_at: string;
};

export type ComplianceCheck = {
  id: string;
  organization_id: string;
  compliance_item_id: string;
  compliance_item_name?: string | null;
  owner_user_id: string;
  owner_display: string | null;
  valid_until: string;
  status: string;
  last_reviewed_at: string | null;
  created_at: string;
  updated_at: string;
  days_until_expiry?: number | null;
};

export type ComplianceDashboard = {
  organization_id: string;
  catalog_count: number;
  checks_active: number;
  checks_expiring_soon: number;
  checks_expired: number;
  assignments_count: number;
  provider_traits_count: number;
  region_traits_count: number;
};

export type AssetCriticality = {
  organization_id: string;
  resource_type: "project" | "vm" | "network";
  project_id: string;
  agent_id?: string | null;
  name?: string | null;
  compliance_items: ComplianceItem[];
  inherited_compliance_items?: ComplianceItem[];
  aggregate_compliance_items?: ComplianceItem[];
  placement_note: string | null;
  updated_at: string | null;
};

export type ComplianceExplorerRow = {
  resource_type: "project" | "vm" | "network";
  project_id: string;
  project_name?: string | null;
  agent_id?: string | null;
  agent_name?: string | null;
  name?: string | null;
  region_id?: string | null;
  region_name?: string | null;
  infrastructure_provider_id?: string | null;
  catalog_items: ComplianceItem[];
  direct_catalog_items?: ComplianceItem[];
  inherited_catalog_items?: ComplianceItem[];
  /** Project only: standards every child VM/network satisfies. */
  aggregate_catalog_items?: ComplianceItem[];
  inherited_traits: PlacementRationale["inherited_traits"];
  placement_note?: string | null;
};

export type ComplianceExplorerResult = {
  organization_id: string;
  filter_description: string;
  total_matched: number;
  offset: number;
  page_size: number;
  truncated: boolean;
  rows: ComplianceExplorerRow[];
};

export type ComplianceExplorerSuggestion = {
  resource_key: string;
  resource_type: "project" | "vm" | "network";
  label: string;
  project_id: string;
  project_name?: string | null;
  agent_id?: string | null;
  name?: string | null;
};

export type ComplianceExplorerSuggestResult = {
  organization_id: string;
  query: string;
  suggestions: ComplianceExplorerSuggestion[];
};

export type ComplianceExplorerFacets = {
  organization_id: string;
  catalog_items: ComplianceItem[];
  trait_keys: string[];
};

export type PlacementRationale = {
  organization_id: string;
  resource_type: "project" | "vm" | "network";
  project_id: string;
  agent_id?: string | null;
  name?: string | null;
  project_name?: string | null;
  agent_name?: string | null;
  region_id?: string | null;
  infrastructure_provider_id?: string | null;
  inherited_traits: {
    scope: "provider" | "region";
    trait_key: string;
    title: string;
    description: string | null;
    moscow: MoscowKind;
    infrastructure_provider_id?: string | null;
    infrastructure_provider_name?: string | null;
    region_id?: string | null;
    region_name?: string | null;
  }[];
  compliance_items: ComplianceItem[];
  inherited_compliance_items?: ComplianceItem[];
  placement_note: string | null;
  related_checks: ComplianceCheck[];
  config_drift?: boolean | null;
};
