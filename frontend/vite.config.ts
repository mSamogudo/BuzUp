import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget = env.VITE_API_PROXY_TARGET;

  return {
    plugins: [react()],
    build: {
      // react-snap pre-renders with an older bundled Chromium that cannot parse
      // optional chaining / nullish coalescing (ES2020). Targeting ES2019 makes
      // esbuild transpile those down so the pre-render JS executes. Also widens
      // real-browser support at a small bundle cost.
      target: "es2019",
      rollupOptions: {
        output: {
          // Split heavy, rarely-changing vendors into long-cacheable chunks so
          // an app deploy doesn't bust them, and so leaflet/recharts only load
          // on the routes that lazy-import them.
          manualChunks: {
            "react-vendor": ["react", "react-dom", "react-router-dom"],
            leaflet: ["leaflet", "react-leaflet"],
            charts: ["recharts"],
          },
        },
      },
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
