/** Built-in roles and permissions (mirrors services/iam/src/huy_iam/roles.py). */

export const PLATFORM_ROLES = ["platform_admin"] as const;

export const ORG_ROLES = ["admin", "compliance_admin", "compliance_engineer"] as const;

export const PROJECT_ROLES = [
  "project_admin",
  "operator",
  "resource_manager",
  "auditor",
  "compliance_reader",
  "ssh_access",
  "security_engineer",
  "compliance_engineer",
] as const;

export const ROLE_CATALOG: {
  scope: string;
  role: string;
  permissions: string[];
}[] = [
  {
    scope: "platform",
    role: "platform_admin",
    permissions: [
      "org:read",
      "org:manage_users",
      "org:manage",
      "platform:manage_orgs",
      "platform:assign_platform_admin",
      "agent:register",
      "agent:export_token",
      "inventory:read",
      "project:read",
      "project:manage",
      "project:operate",
    ],
  },
  {
    scope: "organization",
    role: "admin",
    permissions: [
      "org:read",
      "org:manage_users",
      "inventory:read",
      "project:read",
      "project:manage",
      "project:operate",
    ],
  },
  {
    scope: "organization",
    role: "compliance_admin",
    permissions: ["org:read", "inventory:read"],
  },
  {
    scope: "organization",
    role: "compliance_engineer",
    permissions: ["org:read", "inventory:read"],
  },
  {
    scope: "project",
    role: "project_admin",
    permissions: ["org:read", "project:read", "project:manage", "project:operate"],
  },
  {
    scope: "project",
    role: "operator",
    permissions: ["org:read", "project:read", "project:operate"],
  },
  {
    scope: "project",
    role: "resource_manager",
    permissions: ["org:read", "project:read", "project:operate"],
  },
  {
    scope: "project",
    role: "auditor",
    permissions: ["org:read", "inventory:read"],
  },
  {
    scope: "project",
    role: "compliance_reader",
    permissions: ["org:read", "inventory:read"],
  },
];
