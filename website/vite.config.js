import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: '/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: '../docs',
    emptyOutDir: false, // Don't delete registry.json
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'scheduler'],
          icons: ['lucide-react'],
          ui: ['@/components/ui/card', '@/components/ui/badge', '@/components/ui/button', '@/components/ui/input', '@/components/ui/dialog', '@/components/ui/separator', '@/components/ui/tooltip', '@/components/ui/tabs']
        },
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]'
      }
    },
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true,
        passes: 2,
        pure_funcs: ['console.log', 'console.info', 'console.debug']
      },
      format: {
        comments: false
      }
    },
    cssCodeSplit: true,
    cssMinify: 'lightningcss',
    sourcemap: false,
    target: 'es2015',
    assetsInlineLimit: 8192, // Increased from 4096 to inline more assets
    reportCompressedSize: true,
    chunkSizeWarningLimit: 600,
    modulePreload: {
      polyfill: false // Disable polyfill for faster loading
    }
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