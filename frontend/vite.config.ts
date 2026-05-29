import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/health': 'http://localhost:8000',
      '/papers': 'http://localhost:8000',
      '/chat':   'http://localhost:8000',
    },
  },
})
