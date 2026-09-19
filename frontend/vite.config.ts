import path from "node:path";
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget = env.VITE_API_PROXY_TARGET;

  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      // Os componentes shadcn importam-se por "@/..."; o alias evita
      // reescrever 39 ficheiros e mante-los alinhados com a origem.
      alias: { "@": path.resolve(__dirname, "./src") },
    },
    server: proxyTarget
      ? {
          proxy: {
            "/api": {
              target: proxyTarget,
              changeOrigin: true,
            },
            "/admin": {
              target: proxyTarget,
              changeOrigin: true,
            },
            "/static": {
              target: proxyTarget,
              changeOrigin: true,
            },
            "/media": {
              target: proxyTarget,
              changeOrigin: true,
            },
          },
        }
      : undefined,
  };
});
