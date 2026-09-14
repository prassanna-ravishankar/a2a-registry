import React, { useEffect, useMemo, useRef, useState } from 'react';
import AgentRow from './AgentRow';
import { api, fetchStaticRegistry } from '@/lib/api';

const EMPTY_FILTERS = { q: '', tag: '', conformance: '', healthy: '' };

function readFilters() {
  if (typeof window === 'undefined') return EMPTY_FILTERS;
  const params = new URLSearchParams(window.location.search);
  return Object.fromEntries(Object.keys(EMPTY_FILTERS).map((key) => [key, params.get(key) || '']));
}

export default function RegistryTable({ initialAgents, initialTotal }) {
  const [filters, setFilters] = useState(readFilters);
  const [agents, setAgents] = useState(initialAgents);
  const [total, setTotal] = useState(initialTotal);
  const [status, setStatus] = useState('ready');
  const firstQuery = useRef(true);
  const tags = useMemo(() => Array.from(new Set(initialAgents.flatMap((agent) =>
    (agent.skills || []).flatMap((skill) => skill.tags || []),
  ))).sort((a, b) => a.localeCompare(b)).slice(0, 250), [initialAgents]);

  function update(key, value) {
    const next = { ...filters, [key]: value };
    setFilters(next);
    const params = new URLSearchParams();
    Object.entries(next).forEach(([name, entry]) => entry && params.set(name, entry));
    window.history.replaceState({}, '', `${window.location.pathname}${params.size ? `?${params}` : ''}`);
  }

  useEffect(() => {
    if (firstQuery.current) {
      firstQuery.current = false;
      if (Object.values(filters).every((value) => !value)) return undefined;
    }
    const timer = setTimeout(async () => {
      setStatus('loading');
      try {
        const data = await api.getAgents({
          search: filters.q || undefined,
          skill: filters.tag || undefined,
          conformance: filters.conformance || undefined,
          healthy: filters.healthy === '' ? undefined : filters.healthy === 'true',
          limit: 200,
        });
        setAgents(data.agents || []);
        setTotal(data.total ?? data.agents?.length ?? 0);
        setStatus('ready');
      } catch {
        const snapshot = await fetchStaticRegistry();
        const q = filters.q.toLowerCase();
        const list = (snapshot.agents || []).filter((agent) => {
          const searchable = [agent.name, agent.description, agent.author].join(' ').toLowerCase();
          const tagged = !filters.tag || (agent.skills || []).some((skill) => (skill.tags || []).includes(filters.tag));
          const conformant = !filters.conformance || (filters.conformance === 'standard' ? agent.conformance === true : agent.conformance !== true);
          const healthy = filters.healthy === '' || String(agent.is_healthy) === filters.healthy;
          return (!q || searchable.includes(q)) && tagged && conformant && healthy;
        });
        setAgents(list);
        setTotal(list.length);
        setStatus('offline');
      }
    }, filters.q ? 250 : 0);
    return () => clearTimeout(timer);
  }, [filters]);

  return (
    <section className="registry-browser" aria-busy={status === 'loading'}>
      <form className="registry-filters" onSubmit={(event) => event.preventDefault()}>
        <label className="registry-search"><span>Search the register</span><input value={filters.q} onChange={(event) => update('q', event.target.value)} placeholder="Agent, provider, or capability" type="search" /></label>
        <label><span>Tag</span><select value={filters.tag} onChange={(event) => update('tag', event.target.value)}><option value="">All tags</option>{tags.map((tag) => <option key={tag}>{tag}</option>)}</select></label>
        <label><span>Conformance</span><select value={filters.conformance} onChange={(event) => update('conformance', event.target.value)}><option value="">Any state</option><option value="standard">Conformant</option><option value="non-standard">Non-conformant</option></select></label>
        <label><span>Reachability</span><select value={filters.healthy} onChange={(event) => update('healthy', event.target.value)}><option value="">Any state</option><option value="true">Reachable</option><option value="false">Unreachable</option></select></label>
      </form>
      <div className="registry-result-line"><span>{status === 'loading' ? 'Updating register…' : `${total} matching agents`}</span>{status === 'offline' && <span className="caveat">Offline snapshot</span>}</div>
      <div className="agent-table" role="table" aria-label="Registered A2A agents">
        <div className="agent-table__head" role="row"><span>Name / provider</span><span>Protocol</span><span>Uptime</span><span>Evidence</span><span>Last checked</span><span /></div>
        {agents.map((agent) => <AgentRow key={agent.id} agent={agent} />)}
      </div>
      {status !== 'loading' && agents.length === 0 && <p className="registry-empty">No agents match these parameters. Clear one or more filters.</p>}
    </section>
  );
}
