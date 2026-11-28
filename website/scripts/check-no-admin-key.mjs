// Runs after every `npm run build`: fail if the admin key appears anywhere in the built
// site or Astro's build cache. Prints file paths only, never the key.
import { adminKey, filesContaining } from '../src/lib/adminKey.js';

const key = adminKey();
if (!key) {
  console.log('[check-no-admin-key] no admin key configured; nothing to check');
  process.exit(0);
}
const outDir = process.env.ASTRO_OUT_DIR || '../docs';
const hits = filesContaining(key, [outDir, '.astro']);
if (hits.length) {
  console.error(`[check-no-admin-key] the admin key appears in ${hits.length} build file(s):\n${hits.join('\n')}`);
  process.exit(1);
}
console.log(`[check-no-admin-key] admin key absent from ${outDir} and .astro`);
