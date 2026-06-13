import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/evaluate': 'http://localhost:8000',
      '/timeline': 'http://localhost:8000',
      '/scenarios': 'http://localhost:8000'
    }
  }
})
