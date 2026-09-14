import { loadRegistry } from '@/lib/registryBuild';

export const prerender = true;

export async function GET() {
  return new Response(JSON.stringify(await loadRegistry()), {
    headers: { 'Content-Type': 'application/json; charset=utf-8' },
  });
}
