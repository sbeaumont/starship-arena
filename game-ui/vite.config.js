import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
// In dev, the Svelte app calls the game API on a relative `/api/...` path and Vite
// forwards those calls to the FastAPI server. Same-origin from the browser's point of
// view, so there's no CORS to deal with, and the app code needs no hardcoded host.
export default defineConfig({
  plugins: [svelte()],
  // Reference assets relatively, so the built app works wherever it is mounted - at the root
  // in development and under /play/ when one WSGI app serves everything. With an absolute base
  // the browser would ask for /assets/... and miss the mount point entirely.
  base: './',
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})