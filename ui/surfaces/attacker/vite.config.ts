import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  root: resolve(__dirname, './'),
  server: {
    port: 3003,
    proxy: {
      '/attacker': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
        secure: false
      }
    }
  }
})
