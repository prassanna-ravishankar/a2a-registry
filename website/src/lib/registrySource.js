// What the static build reads from the registry API. With the admin key that is
// one GET /admin/snapshot (every public agent, each one's 30-day uptime, stats and
// categories). Without a key (PR CI, local builds), or while a backend without
// /admin/snapshot is live (CI builds the frontend before the backend deploys), the
// build uses the paced per-resource endpoints instead. A key the API rejects fails
// the build.
//
// fetchJson(path, { allowMissing, headers }) returns parsed JSON, or null for a 404
// when allowMissing is set, and throws on anything else.

export function createRegistrySource(fetchJson, { adminKey, warn = console.warn } = {}) {
  let snapshotPromise;
  let registryPromise;
  let categoriesPromise;

  async function fetchSnapshot() {
    if (!adminKey) {
      warn('[registry] no admin key; using the per-agent endpoints');
      return null;
    }
    const data = await fetchJson('/admin/snapshot', { allowMissing: true, headers: { 'X-Admin-Key': adminKey } });
    if (!data) {
      warn('[registry] GET /admin/snapshot is not deployed; using the per-agent endpoints');
      return null;
    }
    if (data.agents.length !== data.total) {
      throw new Error(`/admin/snapshot holds ${data.agents.length} of ${data.total} agents`);
    }
    return data;
  }

  function snapshot() {
    snapshotPromise ??= fetchSnapshot();
    return snapshotPromise;
  }

  async function listAgentsPaged() {
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
    return { agents, total };
  }

  return {
    loadRegistry() {
      registryPromise ??= (async () => {
        const data = await snapshot();
        const { agents, total } = data ?? (await listAgentsPaged());
        // The edge may serve a snapshot up to a minute old; say when its data was read.
        return { agents, total, generated_at: data?.generated_at ?? new Date().toISOString() };
      })();
      return registryPromise;
    },

    async loadRegistryStats() {
      const data = await snapshot();
      return data ? data.stats : fetchJson('/stats');
    },

    // Category slugs, labels and descriptions are defined once in the backend
    // (app/categories.py). A backend without /categories must not fail the
    // build; the page fills them in live.
    loadCategories() {
      categoriesPromise ??= snapshot().then(async (data) =>
        data ? data.categories : ((await fetchJson('/categories', { allowMissing: true })) ?? []),
      );
      return categoriesPromise;
    },

    // null means no checks in the period, as the per-agent endpoint's 404 does.
    async loadAgentUptime(agentId) {
      const data = await snapshot();
      if (data) return data.uptime[agentId] ?? null;
      return fetchJson(`/agents/${agentId}/uptime?period_days=30`, { allowMissing: true });
    },
  };
}
