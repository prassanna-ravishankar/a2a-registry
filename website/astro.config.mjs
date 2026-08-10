import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';

const outDir = process.env.ASTRO_OUT_DIR || '../docs';

export default defineConfig({
  site: 'https://a2aregistry.org',
  outDir,
  trailingSlash: 'ignore',
  integrations: [
    react(),
    sitemap({ filter: (page) => !page.includes('/admin') }),
  ],
  build: {
    assets: 'assets',
    inlineStylesheets: 'auto',
  },
  vite: {
    resolve: {
      alias: {
        '@': new URL('./src', import.meta.url).pathname,
      },
    },
  },
});
