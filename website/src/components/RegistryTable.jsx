import React, { useMemo, useState } from 'react';
import AgentRow from './AgentRow';
const EMPTY = { q: '', tag: '', conformance: '', healthy: '' };
function readFilters() { if (typeof window === 'undefined') return EMPTY; const p = new URLSearchParams(location.search); return Object.fromEntries(Object.keys(EMPTY).map((key) => [key, p.get(key) || ''])); }
export default function RegistryTable({ initialAgents, initialTotal }) {
  const [filters, setFilters] = useState(readFilters);
  const tags = useMemo(() => Array.from(new Set(initialAgents.flatMap((agent) => (agent.skills || []).flatMap((skill) => skill.tags || [])))).sort((a, b) => a.localeCompare(b)).slice(0, 250), [initialAgents]);
  const agents = useMemo(() => { const q = filters.q.toLowerCase(); return initialAgents.filter((agent) => { const searchable = [agent.name, agent.description, agent.author].join(' ').toLowerCase(); const tagged = !filters.tag || (agent.skills || []).some((skill) => (skill.tags || []).includes(filters.tag)); const conformant = !filters.conformance || (filters.conformance === 'standard' ? agent.conformance === true : agent.conformance !== true); const healthy = filters.healthy === '' || String(agent.is_healthy) === filters.healthy; return (!q || searchable.includes(q)) && tagged && conformant && healthy; }); }, [filters, initialAgents]);
  function update(key, value) { const next = { ...filters, [key]: value }; setFilters(next); const p = new URLSearchParams(); Object.entries(next).forEach(([name, entry]) => entry && p.set(name, entry)); history.replaceState({}, '', `${location.pathname}${p.size ? `?${p}` : ''}`); }
  return <section className="registry-browser">
    <form className="registry-filters" onSubmit={(event) => event.preventDefault()}>
      <label className="registry-search"><span>Search the register</span><input value={filters.q} onChange={(event) => update('q', event.target.value)} placeholder="Agent, provider, or capability" type="search" /></label>
      <label><span>Tag</span><select value={filters.tag} onChange={(event) => update('tag', event.target.value)}><option value="">All tags</option>{tags.map((tag) => <option key={tag}>{tag}</option>)}</select></label>
      <label><span>Conformance</span><select value={filters.conformance} onChange={(event) => update('conformance', event.target.value)}><option value="">Any state</option><option value="standard">Conformant</option><option value="non-standard">Non-conformant</option></select></label>
      <label><span>Reachability</span><select value={filters.healthy} onChange={(event) => update('healthy', event.target.value)}><option value="">Any state</option><option value="true">Reachable</option><option value="false">Unreachable</option></select></label>
    </form>
    <div className="registry-result-line" role="status" aria-live="polite"><span>{agents.length} matching agents{agents.length === initialTotal ? '' : ` of ${initialTotal}`}</span></div>
    <div className="agent-table" aria-label="Registered A2A agents"><div className="agent-table__head" aria-hidden="true"><span>Name / provider</span><span>Protocol</span><span>Uptime</span><span>Evidence</span><span>Last checked</span><span /></div>{agents.map((agent) => <AgentRow key={agent.id} agent={agent} />)}</div>
    {agents.length === 0 && <p className="registry-empty">No agents match these parameters. Clear one or more filters.</p>}
  </section>;
}
