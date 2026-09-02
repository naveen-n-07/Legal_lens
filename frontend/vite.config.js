import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/results': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/docs': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/openapi.json': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
