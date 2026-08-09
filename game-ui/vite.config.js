import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
// In dev, the Svelte app calls the game API on a relative `/api/...` path and Vite
// forwards those calls to the FastAPI server. Same-origin from the browser's point of
// view, so there's no CORS to deal with, and the app code needs no hardcoded host.
export default defineConfig({
  plugins: [svelte()],
  // Reference assets relatively, so the built app works wherever it is served from. It sits at
  // the root both in development and deployed, but an absolute base would tie it to that.
  base: './',
  server: {
    // Every interface, so a phone on the same network can open the map. Vite still reaches the
    // API over localhost itself, so only this one port has to be exposed.
    host: true,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})