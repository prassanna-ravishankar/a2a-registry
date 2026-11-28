// Build-time API client that stays under the edge rate limit by design: at most
// `concurrency` requests in flight and request starts spaced 1/ratePerSecond apart.
// A 429 or 503 is retried after its Retry-After, up to maxAttempts in total.

const RETRY_STATUSES = new Set([429, 503]);

export function retryDelayMs(response, attempt) {
  const seconds = Number(response.headers.get('retry-after'));
  if (Number.isFinite(seconds) && seconds > 0) return Math.min(seconds, 60) * 1000;
  return 2 ** attempt * 1000;
}

export function createPacedFetch({
  fetch = globalThis.fetch,
  ratePerSecond = 8,
  concurrency = 4,
  maxAttempts = 4,
  timeoutMs = 30000,
  now = () => Date.now(),
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
} = {}) {
  const interval = 1000 / ratePerSecond;
  const waiting = [];
  let active = 0;
  let nextStart = 0;

  async function acquire() {
    if (active < concurrency) active += 1;
    else await new Promise((resolve) => waiting.push(resolve)); // slot handed over by release()
    const start = Math.max(now(), nextStart);
    nextStart = start + interval;
    const wait = start - now();
    if (wait > 0) await sleep(wait);
  }

  function release() {
    const next = waiting.shift();
    if (next) next();
    else active -= 1;
  }

  async function attemptOnce(url, init) {
    await acquire();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(url, { ...init, signal: controller.signal });
    } finally {
      clearTimeout(timer);
      release();
    }
  }

  return async function pacedFetch(url, init = {}) {
    for (let attempt = 1; ; attempt += 1) {
      const response = await attemptOnce(url, init);
      if (!RETRY_STATUSES.has(response.status) || attempt >= maxAttempts) return response;
      await sleep(retryDelayMs(response, attempt));
    }
  };
}
