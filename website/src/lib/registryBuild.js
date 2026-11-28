import { createPacedFetch } from './pacedFetch.js';

const SITE = (import.meta.env.SITE || 'https://a2aregistry.org').replace(/\/+$/, '');
const API_BASE = (import.meta.env.PUBLIC_API_URL || `${SITE}/api`).replace(/\/+$/, '');

let registryPromise;

// One shared pacer for the whole build: about 800 prerendered pages each fetch
// uptime, and an unpaced burst trips the edge rate limit on /api.
const pacedFetch = createPacedFetch();

// A 404 is a real answer (no uptime recorded yet, or a backend without that
// route) and returns null. Anything else that is not ok fails the build, so a
// page never ships with its data silently missing.
async function fetchJson(path, { allowMissing = false } = {}) {
  const response = await pacedFetch(`${API_BASE}${path}`);
  if (allowMissing && response.status === 404) return null;
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return await response.json();
}

export function loadRegistry() {
  if (!registryPromise) {
    registryPromise = (async () => {
      const agents = [];
      // The public API caps pages at 100 even when a larger limit is requested.
      const pageSize = 100;
      let total = 0;
      for (let offset = 0; offset < 10000; offset += pageSize) {
        const data = await fetchJson(`/agents?limit=${pageSize}&offset=${offset}`);
        const batch = data.agents || [];
        agents.push(...batch);
        total = data.total ?? agents.length;
        if (batch.length < pageSize || agents.length >= total) break;
      }
      return { agents, total, generated_at: new Date().toISOString() };
    })();
  }
  return registryPromise;
}

export function loadRegistryStats() { return fetchJson('/stats'); }

let categoriesPromise;
// Category slugs, labels and descriptions are defined once in the backend (app/categories.py).
export function loadCategories() {
  // CI builds the frontend before the backend deploys, so a backend without
  // /categories must not fail the build; the page fills them in live.
  if (!categoriesPromise) categoriesPromise = fetchJson('/categories', { allowMissing: true }).then((c) => c ?? []);
  return categoriesPromise;
}
export function loadAgentUptime(agentId) {
  return fetchJson(`/agents/${agentId}/uptime?period_days=30`, { allowMissing: true });
}
