import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/health': 'http://localhost:8000',
      '/papers': 'http://localhost:8000',
      '/chat':   'http://localhost:8000',
    },
    watch: {
      // Ignore lockfiles and pnpm workspace config — they change during installs
      // and were causing Vite to restart in a loop.
      ignored: ['**/pnpm-lock.yaml', '**/pnpm-workspace.yaml', '**/.pnpm/**', '**/node_modules/**'],
    },
  },
})
