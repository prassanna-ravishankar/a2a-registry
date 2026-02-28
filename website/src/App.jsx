import React, { useState, useEffect, useMemo, useCallback } from 'react';
import Layout from './components/Layout';
import AgentGrid from './components/AgentGrid';
import Submit from './pages/Submit';
import Admin from './pages/Admin';
import { api, fetchStaticRegistry } from './lib/api';
import { trackAgentView, trackSearch, trackFilterChange } from './lib/analytics';

function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

const A2ARegistry = () => {
  // Initialize page from URL path
  const [currentPage, setCurrentPage] = useState(() => {
    const p = window.location.pathname;
    if (p === '/submit') return 'submit';
    if (p === '/admin') return 'admin';
    return 'home';
  });
  const [agents, setAgents] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [conformanceFilter, setConformanceFilter] = useState('standard'); // 'all', 'standard', 'non-standard'
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [stats, setStats] = useState(null);
  const [useStaticFallback, setUseStaticFallback] = useState(false);

  const debouncedSearch = useDebounce(searchTerm, 300);

  const LIMIT = 50;

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setSelectedAgent(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Fetch from API with given offset, optionally appending results
  const fetchFromAPI = useCallback(async (offset, append = false) => {
    const skillParam = selectedSkills.length === 1 ? selectedSkills[0] : undefined;

    const data = await api.getAgents({
      search: debouncedSearch || undefined,
      skill: skillParam,
      conformance: conformanceFilter !== 'all' ? conformanceFilter : undefined,
      limit: LIMIT,
      offset,
    });

    const agentList = data.agents || [];
    const totalCount = data.total ?? agentList.length;

    if (debouncedSearch) {
      trackSearch(debouncedSearch, totalCount);
    }

    if (append) {
      setAgents(prev => [...prev, ...agentList]);
    } else {
      setAgents(agentList);
    }
    setTotal(totalCount);
  }, [debouncedSearch, selectedSkills, conformanceFilter]);

  // Initial load and re-fetch when filters change (reset to page 0)
  useEffect(() => {
    let cancelled = false;

    const loadData = async () => {
      setLoading(true);
      setError(null);
      setPage(0);

      try {
        await fetchFromAPI(0, false);
        setUseStaticFallback(false);
        setLoading(false);

        try {
          const statsData = await api.getStats();
          if (!cancelled) setStats(statsData);
        } catch {
          // stats are non-critical
        }
      } catch {
        // Fallback to static registry.json
        try {
          const data = await fetchStaticRegistry();
          const agentList = data.agents || [];
          if (!cancelled) {
            setAgents(agentList);
            setTotal(agentList.length);
            setUseStaticFallback(true);
            setLoading(false);
          }
        } catch {
          if (!cancelled) {
            setError('Failed to load agent registry');
            setLoading(false);
          }
        }
      }
    };

    loadData();
    return () => { cancelled = true; };
  }, [debouncedSearch, selectedSkills, conformanceFilter]);

  // Load more handler
  const handleLoadMore = useCallback(async () => {
    const nextPage = page + 1;
    const offset = nextPage * LIMIT;
    setLoadingMore(true);
    try {
      await fetchFromAPI(offset, true);
      setPage(nextPage);
    } finally {
      setLoadingMore(false);
    }
  }, [page, fetchFromAPI]);

  // Client-side filtering for static fallback
  const filteredAgents = useMemo(() => {
    if (!useStaticFallback) return agents;

    let filtered = agents.filter(agent =>
      agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      agent.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (agent.author && agent.author.toLowerCase().includes(searchTerm.toLowerCase())) ||
      agent.skills.some(skill =>
        skill.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        skill.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    );

    if (selectedSkills.length > 0) {
      filtered = filtered.filter(agent =>
        agent.skills.some(skill =>
          skill.tags.some(tag => selectedSkills.includes(tag))
        )
      );
    }

    if (conformanceFilter === 'standard') {
      filtered = filtered.filter(agent => agent.conformance === true);
    } else if (conformanceFilter === 'non-standard') {
      filtered = filtered.filter(agent => agent.conformance !== true);
    }

    return filtered;
  }, [useStaticFallback, agents, searchTerm, selectedSkills, conformanceFilter]);

  const displayedAgents = useStaticFallback ? filteredAgents : agents;

  // URL Synchronization
  useEffect(() => {
    if (!loading && agents.length > 0) {
      const params = new URLSearchParams(window.location.search);
      const agentId = params.get('agent');
      if (agentId && !selectedAgent) {
        const found = agents.find(a => a.id === agentId);
        if (found) setSelectedAgent(found);
      }
    }
  }, [loading, agents]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (selectedAgent) {
      const agentId = selectedAgent.id;
      if (params.get('agent') !== agentId) {
        params.set('agent', agentId);
        window.history.pushState({}, '', `?${params.toString()}`);
      }
    } else {
      if (params.has('agent')) {
        params.delete('agent');
        const newUrl = params.toString() ? `?${params.toString()}` : window.location.pathname;
        window.history.pushState({}, '', newUrl);
      }
    }
  }, [selectedAgent]);

  // Handle browser back/forward for agent deep-links
  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const agentId = params.get('agent');
      if (agentId) {
        const found = agents.find(a => a.id === agentId);
        if (found) setSelectedAgent(found);
      } else {
        setSelectedAgent(null);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [agents]);

  // Extract all tags for filter list
  const allTags = useMemo(() => {
    let relevantAgents = agents;
    if (conformanceFilter === 'standard') {
      relevantAgents = agents.filter(agent => agent.conformance !== false);
    } else if (conformanceFilter === 'non-standard') {
      relevantAgents = agents.filter(agent => agent.conformance === false);
    }

    const tagCounts = {};
    relevantAgents.forEach(agent => {
      agent.skills.forEach(skill => {
        (skill.tags || []).forEach(tag => {
          tagCounts[tag] = (tagCounts[tag] || 0) + 1;
        });
      });
    });

    return Object.keys(tagCounts).sort((a, b) => {
      const countDiff = tagCounts[b] - tagCounts[a];
      return countDiff !== 0 ? countDiff : a.localeCompare(b);
    });
  }, [agents, conformanceFilter]);

  const toggleSkillFilter = useCallback((tag) => {
    setSelectedSkills(prev => {
      const newSkills = prev.includes(tag)
        ? prev.filter(t => t !== tag)
        : [...prev, tag];
      trackFilterChange('skill', tag);
      return newSkills;
    });
  }, []);

  const handleAgentSelect = useCallback((agent) => {
    setSelectedAgent(agent);
    trackAgentView(agent);
  }, []);

  // Handle page navigation
  useEffect(() => {
    const handleNavigate = (e) => {
      const link = e.target.closest('a');
      if (link && link.pathname === '/submit') {
        e.preventDefault();
        setCurrentPage('submit');
        window.history.pushState({}, '', '/submit');
      } else if (link && link.pathname === '/admin') {
        e.preventDefault();
        setCurrentPage('admin');
        window.history.pushState({}, '', '/admin');
      } else if (link && link.pathname === '/' && link.origin === window.location.origin) {
        e.preventDefault();
        setCurrentPage('home');
        window.history.pushState({}, '', '/');
      }
    };

    const handlePopState = () => {
      const p = window.location.pathname;
      if (p === '/submit') setCurrentPage('submit');
      else if (p === '/admin') setCurrentPage('admin');
      else setCurrentPage('home');
    };

    document.addEventListener('click', handleNavigate);
    window.addEventListener('popstate', handlePopState);
    return () => {
      document.removeEventListener('click', handleNavigate);
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  if (currentPage === 'submit') return <Submit />;
  if (currentPage === 'admin') return <Admin />;

  const showLoadMore = !useStaticFallback && displayedAgents.length < total;

  return (
    <Layout
      searchTerm={searchTerm}
      setSearchTerm={setSearchTerm}
      agentCount={displayedAgents.length}
      total={total}
      allTags={allTags}
      selectedSkills={selectedSkills}
      toggleSkillFilter={toggleSkillFilter}
      conformanceFilter={conformanceFilter}
      setConformanceFilter={setConformanceFilter}
      selectedAgent={selectedAgent}
      onCloseInspection={() => setSelectedAgent(null)}
      stats={stats}
    >
      <AgentGrid
        agents={displayedAgents}
        loading={loading}
        loadingMore={loadingMore}
        error={error}
        selectedAgent={selectedAgent}
        onAgentSelect={handleAgentSelect}
        onLoadMore={showLoadMore ? handleLoadMore : null}
        total={total}
        onClearFilters={() => {
          setSearchTerm('');
          setSelectedSkills([]);
          setConformanceFilter('standard');
        }}
      />
    </Layout>
  );
};

export default A2ARegistry;
