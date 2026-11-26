import { defineConfig } from 'vite';

const api = process.env.DASHBOARD_API_URL || 'http://127.0.0.1:8001';

export default defineConfig({
  base: '/dashboard-assets/',
  esbuild: { jsx: 'automatic' },
  server: {
    proxy: {
      '/dashboard/': api,
      '/datasets/': api,
      '/storage/': api,
    },
  },
});
