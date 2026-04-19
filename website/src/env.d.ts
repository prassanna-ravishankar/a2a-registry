/// <reference path="../.astro/types.d.ts" />
/// <reference types="astro/client" />

interface ImportMetaEnv {
  readonly PUBLIC_POSTHOG_KEY?: string;
  readonly PUBLIC_POSTHOG_HOST?: string;
  readonly PUBLIC_API_URL?: string;
  readonly ALLOW_EMPTY_AGENT_BUILD?: string;
  readonly MAX_AGENT_PAGES?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
