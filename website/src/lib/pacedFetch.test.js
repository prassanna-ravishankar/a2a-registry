import assert from 'node:assert/strict';
import { test } from 'node:test';

import { createPacedFetch, retryDelayMs } from './pacedFetch.js';

// Virtual time: each sleep resolves at its own due time, earliest first, once
// everything runnable has run. clock.run(promise) drives it to completion.
function fakeClock() {
  let t = 0;
  const timers = [];
  return {
    now: () => t,
    sleep: (ms) => new Promise((resolve) => timers.push({ at: t + ms, resolve })),
    async run(promise) {
      let done = false;
      promise.finally(() => (done = true)).catch(() => {});
      while (!done) {
        await new Promise((resolve) => setImmediate(resolve));
        if (!timers.length) continue;
        timers.sort((a, b) => a.at - b.at);
        const next = timers.shift();
        t = Math.max(t, next.at);
        next.resolve();
      }
      return promise;
    },
  };
}

const response = (status, headers = {}) => ({ status, headers: new Headers(headers) });

test('request starts are spaced to the rate', async () => {
  const clock = fakeClock();
  const starts = [];
  const paced = createPacedFetch({
    ...clock,
    ratePerSecond: 8,
    fetch: async () => {
      starts.push(clock.now());
      return response(200);
    },
  });

  await clock.run(Promise.all(Array.from({ length: 20 }, (_, i) => paced(`/x/${i}`))));

  assert.equal(starts.length, 20);
  starts.slice(1).forEach((t, i) => assert.ok(t - starts[i] >= 125, `gap ${t - starts[i]}ms`));
  assert.ok(starts.at(-1) >= 19 * 125);
});

test('never more than `concurrency` requests in flight', async () => {
  let inFlight = 0;
  let peak = 0;
  const clock = fakeClock();
  const paced = createPacedFetch({
    ...clock,
    concurrency: 3,
    fetch: async () => {
      inFlight += 1;
      peak = Math.max(peak, inFlight);
      await clock.sleep(1000); // outlasts the pacing interval, so the cap is what binds
      inFlight -= 1;
      return response(200);
    },
  });

  await clock.run(Promise.all(Array.from({ length: 12 }, (_, i) => paced(`/x/${i}`))));
  assert.equal(peak, 3);
});

test('429 is retried after Retry-After, then succeeds', async () => {
  const clock = fakeClock();
  const statuses = [429, 200];
  const paced = createPacedFetch({ ...clock, fetch: async () => response(statuses.shift(), { 'retry-after': '10' }) });

  const result = await clock.run(paced('/stats'));
  assert.equal(result.status, 200);
  assert.ok(clock.now() >= 10000);
});

test('retries stop after maxAttempts and hand back the last response', async () => {
  let calls = 0;
  const clock = fakeClock();
  const paced = createPacedFetch({
    ...clock,
    maxAttempts: 3,
    fetch: async () => {
      calls += 1;
      return response(429);
    },
  });

  assert.equal((await clock.run(paced('/stats'))).status, 429);
  assert.equal(calls, 3);
});

test('other errors are not retried', async () => {
  let calls = 0;
  const clock = fakeClock();
  const paced = createPacedFetch({
    ...clock,
    fetch: async () => {
      calls += 1;
      return response(500);
    },
  });

  assert.equal((await clock.run(paced('/stats'))).status, 500);
  assert.equal(calls, 1);
});

test('retry delay honours Retry-After, capped, with backoff fallback', () => {
  assert.equal(retryDelayMs(response(429, { 'retry-after': '7' }), 1), 7000);
  assert.equal(retryDelayMs(response(429, { 'retry-after': '600' }), 1), 60000);
  assert.equal(retryDelayMs(response(503), 2), 4000);
});
