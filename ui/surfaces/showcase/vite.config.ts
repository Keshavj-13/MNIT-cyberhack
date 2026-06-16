import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  root: resolve(__dirname, './'),
  server: {
    port: 3004,
    proxy: {
      '/model-reports': {
        target: 'http://localhost:8004',
        changeOrigin: true,
        secure: false
      },
      '/verification-reports': {
        target: 'http://localhost:8004',
        changeOrigin: true,
        secure: false
      },
      '/showcase': {
        target: 'http://localhost:8004',
        changeOrigin: true,
        secure: false
      }
    }
  },
  define: {
    // Override the API base to make all Axios requests relative to Port 3004 dev server
    'import.meta.env.VITE_API_BASE': '""'
  }
})
