import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
// In dev, the Svelte app calls the game API on a relative `/api/...` path and Vite
// forwards those calls to the FastAPI server. Same-origin from the browser's point of
// view, so there's no CORS to deal with, and the app code needs no hardcoded host.
export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})