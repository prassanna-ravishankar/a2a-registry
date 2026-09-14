import { loadRegistry } from '@/lib/registryBuild';
import { trustLevel } from '@/lib/trust';

export async function getStaticPaths() {
  const { agents } = await loadRegistry();
  return agents.map((agent) => ({ params: { slug: agent.id }, props: { agent } }));
}

const xml = (value) => String(value ?? '').replace(/[<>&"']/g, (character) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&apos;' })[character]);

export function GET({ props }) {
  const { agent } = props;
  const trust = trustLevel(agent);
  const marks = trust.evidence.map((passed, index) => {
    const caveat = index === 1 && agent.conformance === false;
    const fill = caveat ? '#b87516' : passed ? '#1f6f4a' : 'none';
    const stroke = caveat ? '#b87516' : passed ? '#1f6f4a' : '#8a8882';
    return `<rect x="${74 + index * 34}" y="348" width="20" height="20" fill="${fill}" stroke="${stroke}" stroke-width="2"/>`;
  }).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630"><rect width="1200" height="630" fill="#f6f5f1"/><path d="M64 82h1072M64 548h1072" stroke="#141414"/><text x="64" y="58" fill="#141414" font-family="monospace" font-size="20">A2A REGISTRY · AGENT RECORD</text><text x="64" y="205" fill="#141414" font-family="sans-serif" font-size="64" font-weight="600">${xml(String(agent.name).slice(0, 32))}</text><text x="66" y="254" fill="#706e68" font-family="sans-serif" font-size="25">${xml(String(agent.provider?.organization || agent.author || 'Provider not declared').slice(0, 60))}</text>${marks}<text x="226" y="366" fill="#1f6f4a" font-family="monospace" font-size="22">${xml(trust.label)}</text><text x="64" y="500" fill="#706e68" font-family="monospace" font-size="18">${xml(String(agent.wellKnownURI).slice(0, 100))}</text></svg>`;
  return new Response(svg, { headers: { 'Content-Type': 'image/svg+xml; charset=utf-8' } });
}
