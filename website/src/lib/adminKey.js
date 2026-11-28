// The admin key for GET /admin/snapshot, read only at build time and only from the
// process environment, never through import.meta.env, so Vite cannot inline it into a
// bundle. The image build mounts it as a BuildKit secret; a local build can set
// REGISTRY_ADMIN_KEY. Without one the build uses the paced public endpoints.
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

export const SECRET_FILE = '/run/secrets/registry_admin_key';

export function adminKey({ env = process.env, secretFile = SECRET_FILE } = {}) {
  const fromEnv = env.REGISTRY_ADMIN_KEY?.trim();
  if (fromEnv) return fromEnv;
  try {
    return readFileSync(secretFile, 'utf8').trim() || undefined;
  } catch {
    return undefined;
  }
}

// Every file under `roots` whose bytes contain `needle`.
export function filesContaining(needle, roots) {
  const hits = [];
  const walk = (path) => {
    if (statSync(path).isDirectory()) readdirSync(path).forEach((name) => walk(join(path, name)));
    else if (readFileSync(path).includes(needle)) hits.push(path);
  };
  roots.filter((root) => existsSync(root)).forEach(walk);
  return hits;
}
