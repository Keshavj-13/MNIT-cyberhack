import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  root: resolve(__dirname, './'),
  server: {
    port: 3002,
    proxy: {
      '/admin': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        secure: false
      }
    }
  }
})
