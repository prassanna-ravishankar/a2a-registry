import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Layout from './Layout';
import AgentGrid from './AgentGrid';
import InspectionDeck from './InspectionDeck';
import { api, fetchStaticRegistry } from '@/lib/api';
import { trackAgentView, trackFilterChange, trackSearch } from '@/lib/analytics';
import useMediaQuery from '@/hooks/useMediaQuery';

const LIMIT = 50;

function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

function agentSlugFromPath(pathname) {
  const match = pathname.match(/^\/agents\/([^/?#]+)\/?$/);
  return match ? decodeURIComponent(match[1]) : null;
}

function pushHomeUrl() {
  if (window.location.pathname !== '/') {
    window.history.pushState({}, '', '/');
  }
}

const HomeApp = () => {
  const getPageScrollTop = () => document.scrollingElement?.scrollTop || window.scrollY || 0;

  const [agents, setAgents] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [conformanceFilter, setConformanceFilter] = useState('standard');
  const [healthyOnly, setHealthyOnly] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [stats, setStats] = useState(null);
  const [useStaticFallback, setUseStaticFallback] = useState(false);
  const isMobile = useMediaQuery('(max-width: 767px)');
  const mobileScrollRef = useRef(0);
  const previousSelectedAgentRef = useRef(null);

  const debouncedSearch = useDebounce(searchTerm, 300);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setSelectedAgent(null);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const fetchFromAPI = useCallback(async (offset, append = false) => {
    const skillParam = selectedSkills.length === 1 ? selectedSkills[0] : undefined;
    const data = await api.getAgents({
      search: debouncedSearch || undefined,
      skill: skillParam,
      conformance: conformanceFilter !== 'all' ? conformanceFilter : undefined,
      healthy: healthyOnly || undefined,
      limit: LIMIT,
      offset,
    });
    const agentList = data.agents || [];
    const totalCount = data.total ?? agentList.length;
    if (debouncedSearch) trackSearch(debouncedSearch, totalCount);
    if (append) setAgents((prev) => [...prev, ...agentList]);
    else setAgents(agentList);
    setTotal(totalCount);
  }, [debouncedSearch, selectedSkills, conformanceFilter, healthyOnly]);

  useEffect(() => {
    let cancelled = false;
    const loadData = async () => {
      setLoading(true);
      setError(null);
      setPage(0);
      try {
        const statsPromise = api.getStats().catch(() => null);
        await fetchFromAPI(0, false);
        setUseStaticFallback(false);
        setLoading(false);
        const statsData = await statsPromise;
        if (!cancelled && statsData) setStats(statsData);
      } catch {
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
  }, [debouncedSearch, selectedSkills, conformanceFilter, healthyOnly, fetchFromAPI]);

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

  const filteredAgents = useMemo(() => {
    if (!useStaticFallback) return agents;
    const q = searchTerm.toLowerCase();
    let filtered = agents.filter((agent) =>
      agent.name.toLowerCase().includes(q) ||
      agent.description.toLowerCase().includes(q) ||
      (agent.author && agent.author.toLowerCase().includes(q)) ||
      agent.skills.some((skill) =>
        skill.name.toLowerCase().includes(q) ||
        skill.tags.some((tag) => tag.toLowerCase().includes(q))
      )
    );
    if (selectedSkills.length > 0) {
      filtered = filtered.filter((agent) =>
        agent.skills.some((skill) => skill.tags.some((tag) => selectedSkills.includes(tag)))
      );
    }
    if (conformanceFilter === 'standard') filtered = filtered.filter((a) => a.conformance === true);
    else if (conformanceFilter === 'non-standard') filtered = filtered.filter((a) => a.conformance !== true);
    return filtered;
  }, [useStaticFallback, agents, searchTerm, selectedSkills, conformanceFilter]);

  const displayedAgents = useStaticFallback ? filteredAgents : agents;

  useEffect(() => {
    const syncFromUrl = async () => {
      const slug = agentSlugFromPath(window.location.pathname);
      if (!slug) {
        setSelectedAgent(null);
        return;
      }
      try {
        const agent = await api.getAgent(slug);
        if (agent) setSelectedAgent(agent);
      } catch {
        setSelectedAgent(null);
      }
    };
    syncFromUrl();
    window.addEventListener('popstate', syncFromUrl);
    return () => window.removeEventListener('popstate', syncFromUrl);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const currentPath = window.location.pathname;
    if (selectedAgent) {
      const target = `/agents/${encodeURIComponent(selectedAgent.id)}`;
      if (currentPath !== target) window.history.pushState({}, '', target);
    } else if (currentPath.startsWith('/agents/')) {
      pushHomeUrl();
    }
  }, [selectedAgent]);

  const allTags = useMemo(() => {
    let relevantAgents = agents;
    if (conformanceFilter === 'standard') relevantAgents = agents.filter((a) => a.conformance !== false);
    else if (conformanceFilter === 'non-standard') relevantAgents = agents.filter((a) => a.conformance === false);
    const tagCounts = {};
    relevantAgents.forEach((agent) => {
      agent.skills.forEach((skill) => {
        (skill.tags || []).forEach((tag) => {
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
    setSelectedSkills((prev) => {
      const newSkills = prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag];
      trackFilterChange('skill', tag);
      return newSkills;
    });
  }, []);

  const handleAgentSelect = useCallback((agent) => {
    if (isMobile) mobileScrollRef.current = getPageScrollTop();
    setSelectedAgent(agent);
    trackAgentView(agent);
  }, [isMobile]);

  const handleCloseInspection = useCallback(() => {
    setSelectedAgent(null);
  }, []);

  useEffect(() => {
    if (isMobile) {
      if (!previousSelectedAgentRef.current && selectedAgent) {
        window.requestAnimationFrame(() => {
          window.requestAnimationFrame(() => {
            window.scrollTo({ top: 0, behavior: 'auto' });
          });
        });
      } else if (previousSelectedAgentRef.current && !selectedAgent) {
        window.requestAnimationFrame(() => {
          window.scrollTo({ top: mobileScrollRef.current, behavior: 'auto' });
        });
      }
    }
    previousSelectedAgentRef.current = selectedAgent;
  }, [isMobile, selectedAgent]);

  const showLoadMore = !useStaticFallback && displayedAgents.length < total;

  return (
    <Layout
      isMobile={isMobile}
      searchTerm={searchTerm}
      setSearchTerm={setSearchTerm}
      agentCount={displayedAgents.length}
      total={total}
      allTags={allTags}
      selectedSkills={selectedSkills}
      toggleSkillFilter={toggleSkillFilter}
      conformanceFilter={conformanceFilter}
      setConformanceFilter={setConformanceFilter}
      healthyOnly={healthyOnly}
      setHealthyOnly={setHealthyOnly}
      selectedAgent={selectedAgent}
      onCloseInspection={handleCloseInspection}
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
          setHealthyOnly(false);
        }}
      />
    </Layout>
  );
};

export default HomeApp;
export { InspectionDeck };
