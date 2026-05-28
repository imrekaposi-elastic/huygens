import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

const cp = (port: number) => ({
  target: `http://127.0.0.1:${port}`,
  changeOrigin: true,
});

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/api/v1/auth": cp(8081),
      "/api/v1/organizations": {
        ...cp(8081),
        router(req) {
          const url = req.url ?? "";
          if (/\/organizations\/[^/]+\/ipam/.test(url)) {
            return "http://127.0.0.1:8084";
          }
          if (
            /\/organizations\/[^/]+\/(compliance-catalog|compliance-checks|compliance-dashboard|compliance-explorer[^?]*|compliance-standards|compliance-controls|compliance-cycles|compliance-packs|compliance-export|compliance-evidence|qualitative-characteristics|regions\/[^/]+\/(traits|compliance-items|characteristics)|traits\/|projects\/[^/]+\/(criticality|resources)|resources\/)/.test(
              url,
            ) ||
            /\/organizations\/[^/]+\/infrastructure-providers\/[^/]+\/(traits|compliance-profile|characteristics)/.test(
              url,
            )
          ) {
            return "http://127.0.0.1:8086";
          }
          return "http://127.0.0.1:8081";
        },
      },
      "/api/v1/platform": cp(8081),
      "/api/v1/users": cp(8081),
      "/api/v1/inventory": cp(8083),
      "/api/v1/projects": cp(8084),
      "/api/v1/agents": cp(8082),
      "/api/v1/providers": cp(8082),
    },
  },
});
