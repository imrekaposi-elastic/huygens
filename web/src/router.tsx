import { createRootRoute, createRoute, createRouter, redirect } from "@tanstack/react-router";
import { AppShell } from "@/layouts/AppShell";
import { RootLayout } from "@/layouts/RootLayout";
import { getAccessToken } from "@/auth/token";
import { LoginPage } from "@/pages/LoginPage";
import { OidcCallbackPage } from "@/pages/OidcCallbackPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { ProjectsPage } from "@/pages/ProjectsPage";
import { AgentsPage } from "@/pages/AgentsPage";
import { AgentTechnologiesGatePage } from "@/pages/AgentTechnologiesGatePage";
import { InfrastructureGatePage } from "@/pages/InfrastructureGatePage";
import { SetupGatePage } from "@/pages/SetupGatePage";
import { ProjectLayout } from "@/pages/project/ProjectLayout";
import { ProjectWorkspaceProvider } from "@/pages/project/projectContext";
import { ProjectCloudInitTab } from "@/pages/project/ProjectCloudInitTab";
import { ProjectVmsTab } from "@/pages/project/ProjectVmsTab";
import { ProjectNetworksTab } from "@/pages/project/ProjectNetworksTab";
import { ProjectAccessTab } from "@/pages/project/ProjectAccessTab";
import { ProjectComplianceTab } from "@/pages/project/ProjectComplianceTab";
import { ProjectImagesTab } from "@/pages/project/ProjectImagesTab";
import { ComplianceGatePage } from "@/pages/compliance/ComplianceGatePage";
import { ComplianceOverviewPage } from "@/pages/compliance/ComplianceOverviewPage";
import { ComplianceExplorerPage } from "@/pages/compliance/ComplianceExplorerPage";
import { ComplianceCatalogPage } from "@/pages/compliance/ComplianceCatalogPage";
import { ComplianceChecksPage } from "@/pages/compliance/ComplianceChecksPage";
import { ComplianceGrcPage } from "@/pages/compliance/ComplianceGrcPage";
import { IpamGatePage } from "@/pages/ipam/IpamGatePage";
import { TopologyGatePage } from "@/pages/topology/TopologyGatePage";
import { AdminGatePage } from "@/pages/admin/AdminGatePage";
import { AdminUsersTab } from "@/pages/admin/AdminUsersTab";
import { AdminIdpMappingsTab } from "@/pages/admin/AdminIdpMappingsTab";
import { AdminAuthenticationTab } from "@/pages/admin/AdminAuthenticationTab";
import { AdminRbacTab } from "@/pages/admin/AdminRbacTab";
import { AccessSessionsPage } from "@/pages/access/AccessSessionsPage";
import { SshTerminalPage } from "@/pages/access/SshTerminalPage";

const rootRoute = createRootRoute({ component: RootLayout });

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: LoginPage,
  beforeLoad: () => {
    if (getAccessToken()) throw redirect({ to: "/" });
  },
});

const oidcCallbackRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/auth/callback",
  component: OidcCallbackPage,
});

const setupRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/setup",
  component: SetupGatePage,
});

const appRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: "app",
  component: AppShell,
  beforeLoad: () => {
    if (!getAccessToken()) throw redirect({ to: "/login" });
  },
});

const indexRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/",
  component: DashboardPage,
});

const agentTechnologiesRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/agent-technologies",
  beforeLoad: () => {
    throw redirect({ to: "/admin/fabric" });
  },
  component: () => null,
});

const infrastructureRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/infrastructure",
  component: InfrastructureGatePage,
});

const agentsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/agents",
  component: AgentsPage,
});

const ipamRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/ipam",
  component: IpamGatePage,
});

const complianceRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/compliance",
  component: ComplianceGatePage,
});

const complianceIndexRoute = createRoute({
  getParentRoute: () => complianceRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/compliance/overview" });
  },
  component: () => null,
});

const complianceOverviewRoute = createRoute({
  getParentRoute: () => complianceRoute,
  path: "/overview",
  component: ComplianceOverviewPage,
});

const complianceExplorerRoute = createRoute({
  getParentRoute: () => complianceRoute,
  path: "/explorer",
  component: ComplianceExplorerPage,
});

const complianceCatalogRoute = createRoute({
  getParentRoute: () => complianceRoute,
  path: "/catalog",
  component: ComplianceCatalogPage,
});

const complianceChecksRoute = createRoute({
  getParentRoute: () => complianceRoute,
  path: "/checks",
  component: ComplianceChecksPage,
});

const complianceGrcRoute = createRoute({
  getParentRoute: () => complianceRoute,
  path: "/grc",
  component: ComplianceGrcPage,
});

const topologyRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/topology",
  component: TopologyGatePage,
});

const adminRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/admin",
  component: AdminGatePage,
});

const adminIndexRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/admin/users" });
  },
  component: () => null,
});

const adminUsersRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "users",
  component: AdminUsersTab,
});

const adminIdpRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "idp",
  component: AdminIdpMappingsTab,
});

const adminAuthRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "authentication",
  component: AdminAuthenticationTab,
});

const adminRbacRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "rbac",
  component: AdminRbacTab,
});

const adminFabricRoute = createRoute({
  getParentRoute: () => adminRoute,
  path: "fabric",
  component: AgentTechnologiesGatePage,
});

const accessRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/access",
  component: AccessSessionsPage,
});

const accessTerminalRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/access/terminal/$sessionId",
  component: SshTerminalPage,
});

const projectsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/projects",
  component: ProjectsPage,
});

const projectRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/projects/$projectId",
  component: function ProjectRoute() {
    const { projectId } = projectRoute.useParams();
    return (
      <ProjectWorkspaceProvider projectId={projectId}>
        <ProjectLayout projectId={projectId} />
      </ProjectWorkspaceProvider>
    );
  },
});

const projectIndexRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "/",
  beforeLoad: ({ params }) => {
    throw redirect({
      to: "/projects/$projectId/vms",
      params: { projectId: params.projectId },
    });
  },
  component: () => null,
});

const projectVmsRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "vms",
  component: function ProjectVmsRoute() {
    const { projectId } = projectRoute.useParams();
    return <ProjectVmsTab projectId={projectId} />;
  },
});

const projectImagesRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "images",
  component: function ProjectImagesRoute() {
    const { projectId } = projectRoute.useParams();
    return <ProjectImagesTab projectId={projectId} />;
  },
});

const projectNetworksRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "networks",
  component: function ProjectNetworksRoute() {
    const { projectId } = projectRoute.useParams();
    return <ProjectNetworksTab projectId={projectId} />;
  },
});

const projectComplianceRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "compliance",
  component: function ProjectComplianceRoute() {
    const { projectId } = projectRoute.useParams();
    return <ProjectComplianceTab projectId={projectId} />;
  },
});

const projectCloudInitRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "cloud-init",
  component: function ProjectCloudInitRoute() {
    const { projectId } = projectRoute.useParams();
    return <ProjectCloudInitTab projectId={projectId} />;
  },
});

const projectAccessRoute = createRoute({
  getParentRoute: () => projectRoute,
  path: "access",
  component: function ProjectAccessRoute() {
    const { projectId } = projectRoute.useParams();
    return <ProjectAccessTab projectId={projectId} />;
  },
});

const routeTree = rootRoute.addChildren([
  loginRoute,
  oidcCallbackRoute,
  setupRoute,
  appRoute.addChildren([
    indexRoute,
    agentTechnologiesRoute,
    infrastructureRoute,
    agentsRoute,
    ipamRoute,
    complianceRoute.addChildren([
      complianceIndexRoute,
      complianceOverviewRoute,
      complianceExplorerRoute,
      complianceCatalogRoute,
      complianceChecksRoute,
      complianceGrcRoute,
    ]),
    topologyRoute,
    accessRoute,
    accessTerminalRoute,
    adminRoute.addChildren([
      adminIndexRoute,
      adminFabricRoute,
      adminUsersRoute,
      adminIdpRoute,
      adminAuthRoute,
      adminRbacRoute,
    ]),
    projectsRoute,
    projectRoute.addChildren([
      projectIndexRoute,
      projectVmsRoute,
      projectImagesRoute,
      projectNetworksRoute,
      projectComplianceRoute,
      projectCloudInitRoute,
      projectAccessRoute,
    ]),
  ]),
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
