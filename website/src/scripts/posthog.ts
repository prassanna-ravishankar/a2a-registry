const key = import.meta.env.PUBLIC_POSTHOG_KEY;
const host = import.meta.env.PUBLIC_POSTHOG_HOST || 'https://us.posthog.com';

if (key) {
  (async () => {
    try {
      const { default: posthog } = await import('posthog-js');
      posthog.init(key, {
        api_host: host,
        autocapture: true,
        capture_pageview: true,
        capture_pageleave: true,
        persistence: 'memory',
        respect_dnt: true,
      });
      (window as unknown as { posthog: typeof posthog }).posthog = posthog;
    } catch {
      // analytics blocked or failed to load — app continues without tracking
    }
  })();
}
