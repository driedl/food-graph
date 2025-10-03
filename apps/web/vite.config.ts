import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'
import path from 'node:path'
import { TanStackRouterVite } from '@tanstack/router-plugin/vite'

export default defineConfig({
  plugins: [
    react(),
    TanStackRouterVite(),
    process.env.ANALYZE ? (visualizer({ filename: 'stats.html' }) as any) : undefined
  ].filter(Boolean),
  server: {
    port: 5173,
    proxy: {
      '/trpc': {
        target: 'http://localhost:3000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom'],
          query: ['@tanstack/react-query'],
          trpc: ['@trpc/client', '@trpc/react-query', 'zod'],
        },
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      '@ui': path.resolve(__dirname, 'src/components/ui'),
      '@lib': path.resolve(__dirname, 'src/lib')
    }
  }
})
