import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The React dev server runs on 5173 and forwards every /api call to the
// FastAPI backend on 8000, so the browser never hits a CORS problem.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  // `npm run preview` serves the production build and needs the same proxy.
  preview: {
    port: 4173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: { outDir: 'dist', sourcemap: false },
})
