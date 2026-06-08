import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default ({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return defineConfig({
    plugins: [react()],
    define: {
      'import.meta.env.VITE_NEO4J_URI': JSON.stringify(env.NEO4J_URI || env.VITE_NEO4J_URI || ''),
      'import.meta.env.VITE_NEO4J_USER': JSON.stringify(env.NEO4J_USER || env.VITE_NEO4J_USER || ''),
      'import.meta.env.VITE_NEO4J_PASSWORD': JSON.stringify(env.NEO4J_PASSWORD || env.VITE_NEO4J_PASSWORD || ''),
    },
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  })
}
