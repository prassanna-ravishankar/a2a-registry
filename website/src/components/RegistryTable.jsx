import React, { useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import { rowAgent, lastSweep } from '@/lib/registryView';
import AgentRow from './AgentRow';
const EMPTY = { q: '', tag: '', conformance: '', healthy: '' };
function readFilters() { if (typeof window === 'undefined') return EMPTY; const p = new URLSearchParams(location.search); return Object.fromEntries(Object.keys(EMPTY).map((key) => [key, p.get(key) || ''])); }
export default function RegistryTable({ initialAgents }) {
  const [filters, setFilters] = useState(EMPTY);
  const [records, setRecords] = useState(initialAgents);
  const [refreshState, setRefreshState] = useState('refreshing');
  useEffect(() => {
    setFilters(readFilters());
    let active = true;
    (async () => {
      const all = [];
      for (let offset = 0; ; offset += 100) {
        const page = await api.getAgents({ limit: 100, offset });
        all.push(...page.agents.map(rowAgent));
        if (page.agents.length < 100 || all.length >= page.total) break;
      }
      if (!active) return;
      const unique = [...new Map(all.map((agent) => [agent.id, agent])).values()];
      setRecords(unique);
      setRefreshState('live');
      const sweep = lastSweep(unique);
      document.getElementById('registry-count').textContent = `${unique.length} agents`;
      document.getElementById('registry-healthy').textContent = `${unique.filter((agent) => agent.is_healthy === true).length} reachable`;
      const time = document.getElementById('registry-sweep');
      time.textContent = sweep ? `sweep ${sweep.slice(0, 16).replace('T', ' ')} UTC` : 'No sweep recorded';
      if (sweep) { time.dateTime = sweep; time.title = sweep; }
    })().catch(() => { if (active) setRefreshState('saved'); });
    return () => { active = false; };
  }, []);
  const tags = useMemo(() => Array.from(new Set(records.flatMap((agent) => agent.tags || []))).sort((a, b) => a.localeCompare(b)).slice(0, 250), [records]);
  const agents = useMemo(() => { const q = filters.q.toLowerCase(); return records.filter((agent) => { const searchable = [agent.name, agent.description, agent.author].join(' ').toLowerCase(); const tagged = !filters.tag || (agent.tags || []).includes(filters.tag); const conformant = !filters.conformance || (filters.conformance === 'standard' ? agent.conformance === true : agent.conformance !== true); const healthy = filters.healthy === '' || String(agent.is_healthy) === filters.healthy; return (!q || searchable.includes(q)) && tagged && conformant && healthy; }); }, [filters, records]);
  function update(key, value) { const next = { ...filters, [key]: value }; setFilters(next); const p = new URLSearchParams(); Object.entries(next).forEach(([name, entry]) => entry && p.set(name, entry)); history.replaceState({}, '', `${location.pathname}${p.size ? `?${p}` : ''}`); }
  return <section className="registry-browser">
    <form className="registry-filters" onSubmit={(event) => event.preventDefault()}>
      <label className="registry-search"><span>Search the register</span><input value={filters.q} onChange={(event) => update('q', event.target.value)} placeholder="Agent, provider, or capability" type="search" /></label>
      <label><span>Tag</span><select value={filters.tag} onChange={(event) => update('tag', event.target.value)}><option value="">All tags</option>{tags.map((tag) => <option key={tag}>{tag}</option>)}</select></label>
      <label><span>Conformance</span><select value={filters.conformance} onChange={(event) => update('conformance', event.target.value)}><option value="">Any state</option><option value="standard">Conformant</option><option value="non-standard">Non-conformant</option></select></label>
      <label><span>Reachability</span><select value={filters.healthy} onChange={(event) => update('healthy', event.target.value)}><option value="">Any state</option><option value="true">Reachable</option><option value="false">Unreachable</option></select></label>
    </form>
    <div className="registry-result-line" role="status" aria-live="polite"><span>{agents.length} matching agents{agents.length === records.length ? '' : ` of ${records.length}`}</span><span>{refreshState === 'saved' ? 'Live refresh unavailable. Showing saved observations.' : refreshState === 'refreshing' ? 'Refreshing observations…' : 'Live observations'}</span></div>
    <div className="agent-table" aria-label="Registered A2A agents"><div className="agent-table__head" aria-hidden="true"><span>Name / provider</span><span>Protocol</span><span>Uptime</span><span>Evidence</span><span>Last checked</span><span /></div>{agents.map((agent) => <AgentRow key={agent.id} agent={agent} />)}</div>
    {agents.length === 0 && <p className="registry-empty">No agents match these parameters. Clear one or more filters.</p>}
  </section>;
}
