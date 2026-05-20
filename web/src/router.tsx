import { Outlet, createRootRoute, createRoute, createRouter, redirect } from "@tanstack/react-router";
import { AppShell } from "@/layouts/AppShell";
import { getAccessToken } from "@/auth/token";
import { LoginPage } from "@/pages/LoginPage";
import { OidcCallbackPage } from "@/pages/OidcCallbackPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { ProjectsPage } from "@/pages/ProjectsPage";
import { ProjectDetailPage } from "@/pages/ProjectDetailPage";
import { AgentsPage } from "@/pages/AgentsPage";

const rootRoute = createRootRoute({ component: () => <Outlet /> });

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

const projectsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/projects",
  component: ProjectsPage,
});

const projectDetailRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/projects/$projectId",
  component: function ProjectDetailRoute() {
    const { projectId } = projectDetailRoute.useParams();
    return <ProjectDetailPage projectId={projectId} />;
  },
});

const agentsRoute = createRoute({
  getParentRoute: () => appRoute,
  path: "/agents",
  component: AgentsPage,
});

const routeTree = rootRoute.addChildren([
  loginRoute,
  oidcCallbackRoute,
  appRoute.addChildren([indexRoute, projectsRoute, projectDetailRoute, agentsRoute]),
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
