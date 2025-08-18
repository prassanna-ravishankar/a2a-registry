import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/',
  build: {
    outDir: '../docs',
    emptyOutDir: false, // Don't delete registry.json
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          icons: ['lucide-react']
        }
      }
    },
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    },
    cssCodeSplit: true,
    sourcemap: false,
    target: 'es2015',
    assetsInlineLimit: 4096
  },
  esbuild: {
    legalComments: 'none'
  },
  server: {
    fs: {
      allow: ['..']
    }
  }
});