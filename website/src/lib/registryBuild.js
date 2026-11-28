import { createPacedFetch } from './pacedFetch.js';
import { createRegistrySource } from './registrySource.js';

const SITE = (import.meta.env.SITE || 'https://a2aregistry.org').replace(/\/+$/, '');
const API_BASE = (import.meta.env.PUBLIC_API_URL || `${SITE}/api`).replace(/\/+$/, '');

// A backstop now that the build normally makes one request: if it ever falls
// back to per-agent endpoints, the pacer keeps it under the edge rate limit on /api.
const pacedFetch = createPacedFetch({
  fetch: (url, init) => {
    globalThis.__registryApiRequests = (globalThis.__registryApiRequests ?? 0) + 1;
    return fetch(url, init);
  },
});

// A 404 is a real answer (no uptime recorded yet, or a backend without that
// route) and returns null. Anything else that is not ok fails the build, so a
// page never ships with its data silently missing.
async function fetchJson(path, { allowMissing = false } = {}) {
  const response = await pacedFetch(`${API_BASE}${path}`);
  if (allowMissing && response.status === 404) return null;
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return await response.json();
}

export const { loadRegistry, loadRegistryStats, loadCategories, loadAgentUptime } = createRegistrySource(fetchJson);
