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
import { ProjectImagesTab } from "@/pages/project/ProjectImagesTab";
import { IpamGatePage } from "@/pages/ipam/IpamGatePage";
import { AdminGatePage } from "@/pages/admin/AdminGatePage";
import { AdminUsersTab } from "@/pages/admin/AdminUsersTab";
import { AdminIdpMappingsTab } from "@/pages/admin/AdminIdpMappingsTab";
import { AdminAuthenticationTab } from "@/pages/admin/AdminAuthenticationTab";
import { AdminRbacTab } from "@/pages/admin/AdminRbacTab";

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
  component: AgentTechnologiesGatePage,
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
    adminRoute.addChildren([
      adminIndexRoute,
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
