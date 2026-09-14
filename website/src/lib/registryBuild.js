const SITE = (import.meta.env.SITE || 'https://a2aregistry.org').replace(/\/+$/, '');
const API_BASE = (import.meta.env.PUBLIC_API_URL || `${SITE}/api`).replace(/\/+$/, '');

let registryPromise;

async function fetchJson(path) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 30000);
  try {
    const response = await fetch(`${API_BASE}${path}`, { signal: controller.signal });
    if (!response.ok) throw new Error(`${path} returned ${response.status}`);
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
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
export function loadAgentUptime(agentId) {
  return fetchJson(`/agents/${agentId}/uptime?period_days=30`).catch(() => null);
}
