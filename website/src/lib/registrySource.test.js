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
  const headersSent = {};
  const fetchJson = async (path, { allowMissing = false, headers } = {}) => {
    requests.push(path);
    if (headers) headersSent[path] = headers;
    if (path in routes) {
      const value = routes[path];
      if (value instanceof Error) throw value;
      return value;
    }
    if (allowMissing) return null;
    throw new Error(`${path} returned 404`);
  };
  return { fetchJson, requests, headersSent };
}

async function renderEverything(source) {
  const registry = await source.loadRegistry();
  const pages = await Promise.all(
    registry.agents.map(async (agent) => ({ uptime: await source.loadAgentUptime(agent.id), categories: await source.loadCategories() })),
  );
  return { registry, stats: await source.loadRegistryStats(), pages };
}

test('with the admin key the build reads everything from one /admin/snapshot request', async () => {
  const api = fakeApi({
    '/admin/snapshot': { generated_at: '2026-11-28T10:00:00Z', total: 2, agents: AGENTS, uptime: { a1: UPTIME_A1 }, stats: STATS, categories: CATEGORIES },
  });

  const { registry, stats, pages } = await renderEverything(createRegistrySource(api.fetchJson, { adminKey: 'k' }));

  assert.deepEqual(api.requests, ['/admin/snapshot']);
  assert.deepEqual(registry.agents, AGENTS);
  assert.equal(registry.total, 2);
  assert.equal(registry.generated_at, '2026-11-28T10:00:00Z'); // a cached snapshot keeps its own time
  assert.deepEqual(stats, STATS);
  assert.deepEqual(pages[0], { uptime: UPTIME_A1, categories: CATEGORIES });
  assert.deepEqual(pages[1], { uptime: null, categories: CATEGORIES }); // no checks yet, like the endpoint's 404
});

test('a backend without /admin/snapshot falls back to the per-resource endpoints', async () => {
  const warnings = [];
  const api = fakeApi({
    '/agents?limit=100&offset=0': { agents: AGENTS, total: 2 },
    '/agents/a1/uptime?period_days=30': UPTIME_A1,
    '/stats': STATS,
    '/categories': CATEGORIES,
  });

  const { registry, stats, pages } = await renderEverything(
    createRegistrySource(api.fetchJson, { adminKey: 'k', warn: (m) => warnings.push(m) }),
  );

  assert.equal(api.requests[0], '/admin/snapshot');
  assert.deepEqual(new Set(api.requests), new Set([
    '/admin/snapshot', '/agents?limit=100&offset=0', '/agents/a1/uptime?period_days=30', '/agents/a2/uptime?period_days=30', '/categories', '/stats',
  ]));
  assert.equal(warnings.length, 1);
  assert.deepEqual(registry.agents, AGENTS);
  assert.deepEqual(stats, STATS);
  assert.deepEqual(pages.map((p) => p.uptime), [UPTIME_A1, null]);
});

test('a snapshot with fewer agents than its total fails the build', async () => {
  const api = fakeApi({ '/admin/snapshot': { total: 3, agents: AGENTS, uptime: {}, stats: STATS, categories: [] } });
  await assert.rejects(createRegistrySource(api.fetchJson, { adminKey: 'k' }).loadRegistry(), /holds 2 of 3 agents/);
});

test('a failing /admin/snapshot fails the build instead of falling back', async () => {
  const api = fakeApi({ '/admin/snapshot': new Error('/admin/snapshot returned 429') });
  await assert.rejects(createRegistrySource(api.fetchJson, { adminKey: 'k' }).loadRegistry(), /429/);
  assert.deepEqual(api.requests, ['/admin/snapshot']);
});

const PER_RESOURCE = {
  '/agents?limit=100&offset=0': { agents: AGENTS, total: 2 },
  '/agents/a1/uptime?period_days=30': UPTIME_A1,
  '/stats': STATS,
  '/categories': CATEGORIES,
};

test('the snapshot request carries the admin key', async () => {
  const api = fakeApi({ '/admin/snapshot': { total: 0, agents: [], uptime: {}, stats: STATS, categories: [] } });
  await createRegistrySource(api.fetchJson, { adminKey: 'secret-key' }).loadRegistry();
  assert.deepEqual(api.headersSent['/admin/snapshot'], { 'X-Admin-Key': 'secret-key' });
});

test('without an admin key the build never asks for the snapshot and uses the public endpoints', async () => {
  const warnings = [];
  const api = fakeApi(PER_RESOURCE);
  const { registry, pages } = await renderEverything(createRegistrySource(api.fetchJson, { warn: (m) => warnings.push(m) }));

  assert.ok(!api.requests.includes('/admin/snapshot'));
  assert.deepEqual(registry.agents, AGENTS);
  assert.deepEqual(pages.map((p) => p.uptime), [UPTIME_A1, null]);
  assert.match(warnings[0], /no admin key/);
});

test('a configured key the API rejects fails the build instead of falling back', async () => {
  for (const status of [401, 403]) {
    const api = fakeApi({ ...PER_RESOURCE, '/admin/snapshot': new Error(`/admin/snapshot returned ${status}`) });
    await assert.rejects(createRegistrySource(api.fetchJson, { adminKey: 'wrong' }).loadRegistry(), new RegExp(String(status)));
    assert.deepEqual(api.requests, ['/admin/snapshot']);
  }
});
