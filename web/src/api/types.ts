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

export type AgentInventorySummary = {
  agent_id: string;
  organization_id: string;
  region_id: string;
  polled_at: string | null;
  config_drift: boolean;
  poll_error: string | null;
  vm_count: number;
  network_count: number;
  connection_status: string | null;
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

export type AgentSummary = {
  id: string;
  name: string;
  base_url: string;
  organization_id: string;
  connection_status: string;
};

export type AgentOut = {
  id: string;
  name: string;
  organization_id: string;
  region_id: string;
  base_url: string;
  connection_status: string;
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
