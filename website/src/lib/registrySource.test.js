import assert from 'node:assert/strict';
import { test } from 'node:test';

import { createRegistrySource } from './registrySource.js';

const AGENTS = [{ id: 'a1', name: 'One' }, { id: 'a2', name: 'Two' }];
const UPTIME_A1 = { period_days: 30, uptime_percentage: 99.5, avg_response_time_ms: 40, history: [{ checked_at: 't', success: true }] };
const STATS = { total_agents: 2 };
const CATEGORIES = [{ slug: 'dev', label: 'Dev', description: 'd', agent_count: 1 }];

// A fake API keyed by path; records every request. A missing path is a 404.
function fakeApi(routes) {
  const requests = [];
  const fetchJson = async (path, { allowMissing = false } = {}) => {
    requests.push(path);
    if (path in routes) {
      const value = routes[path];
      if (value instanceof Error) throw value;
      return value;
    }
    if (allowMissing) return null;
    throw new Error(`${path} returned 404`);
  };
  return { fetchJson, requests };
}

async function renderEverything(source) {
  const registry = await source.loadRegistry();
  const pages = await Promise.all(
    registry.agents.map(async (agent) => ({ uptime: await source.loadAgentUptime(agent.id), categories: await source.loadCategories() })),
  );
  return { registry, stats: await source.loadRegistryStats(), pages };
}

test('the build reads everything from one /snapshot request', async () => {
  const api = fakeApi({
    '/snapshot': { generated_at: '2026-11-28T10:00:00Z', total: 2, agents: AGENTS, uptime: { a1: UPTIME_A1 }, stats: STATS, categories: CATEGORIES },
  });

  const { registry, stats, pages } = await renderEverything(createRegistrySource(api.fetchJson));

  assert.deepEqual(api.requests, ['/snapshot']);
  assert.deepEqual(registry.agents, AGENTS);
  assert.equal(registry.total, 2);
  assert.equal(registry.generated_at, '2026-11-28T10:00:00Z'); // a cached snapshot keeps its own time
  assert.deepEqual(stats, STATS);
  assert.deepEqual(pages[0], { uptime: UPTIME_A1, categories: CATEGORIES });
  assert.deepEqual(pages[1], { uptime: null, categories: CATEGORIES }); // no checks yet, like the endpoint's 404
});

test('a backend without /snapshot falls back to the per-resource endpoints', async () => {
  const warnings = [];
  const api = fakeApi({
    '/agents?limit=100&offset=0': { agents: AGENTS, total: 2 },
    '/agents/a1/uptime?period_days=30': UPTIME_A1,
    '/stats': STATS,
    '/categories': CATEGORIES,
  });

  const { registry, stats, pages } = await renderEverything(
    createRegistrySource(api.fetchJson, { warn: (m) => warnings.push(m) }),
  );

  assert.equal(api.requests[0], '/snapshot');
  assert.deepEqual(new Set(api.requests), new Set([
    '/snapshot', '/agents?limit=100&offset=0', '/agents/a1/uptime?period_days=30', '/agents/a2/uptime?period_days=30', '/categories', '/stats',
  ]));
  assert.equal(warnings.length, 1);
  assert.deepEqual(registry.agents, AGENTS);
  assert.deepEqual(stats, STATS);
  assert.deepEqual(pages.map((p) => p.uptime), [UPTIME_A1, null]);
});

test('a snapshot with fewer agents than its total fails the build', async () => {
  const api = fakeApi({ '/snapshot': { total: 3, agents: AGENTS, uptime: {}, stats: STATS, categories: [] } });
  await assert.rejects(createRegistrySource(api.fetchJson).loadRegistry(), /holds 2 of 3 agents/);
});

test('a failing /snapshot fails the build instead of falling back', async () => {
  const api = fakeApi({ '/snapshot': new Error('/snapshot returned 429') });
  await assert.rejects(createRegistrySource(api.fetchJson).loadRegistry(), /429/);
  assert.deepEqual(api.requests, ['/snapshot']);
});
