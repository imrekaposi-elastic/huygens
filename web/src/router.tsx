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

const routeTree = rootRoute.addChildren([
  loginRoute,
  oidcCallbackRoute,
  setupRoute,
  appRoute.addChildren([
    indexRoute,
    agentTechnologiesRoute,
    infrastructureRoute,
    agentsRoute,
    projectsRoute,
    projectRoute.addChildren([
      projectIndexRoute,
      projectVmsRoute,
      projectNetworksRoute,
      projectCloudInitRoute,
    ]),
  ]),
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
