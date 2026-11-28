import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import sitemap from '@astrojs/sitemap';

const outDir = process.env.ASTRO_OUT_DIR || '../docs';

// src/lib/registryBuild.js counts every request it sends to the registry API.
const registryRequestCount = {
  name: 'registry-request-count',
  hooks: {
    'astro:build:done': ({ logger }) => logger.info(`${globalThis.__registryApiRequests ?? 0} registry API requests`),
  },
};

export default defineConfig({
  site: 'https://a2aregistry.org',
  outDir,
  trailingSlash: 'ignore',
  integrations: [
    react(),
    sitemap({ filter: (page) => !page.includes('/admin') }),
    registryRequestCount,
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
