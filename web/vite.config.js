import { defineConfig } from 'vite';

// Dev: `npm run dev` on :5173 proxies API calls to api.py on :8000.
// Prod: `npm run build` writes web/dist, which api.py serves at "/".
const API = process.env.API_URL ?? 'http://127.0.0.1:8000';

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/api': API,
      '/health': API,
    },
  },
  build: { outDir: 'dist', emptyOutDir: true },
});
