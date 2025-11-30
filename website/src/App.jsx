import React, { useState, useEffect, useMemo, useCallback } from 'react';
import Layout from './components/Layout';
import AgentGrid from './components/AgentGrid';
import Submit from './pages/Submit';
import { api, fetchStaticRegistry } from './lib/api';
import { trackAgentView, trackSearch, trackFilterChange } from './lib/analytics';

const A2ARegistry = () => {
  const [currentPage, setCurrentPage] = useState('home'); // 'home' or 'submit'
  const [agents, setAgents] = useState([]);
  const [filteredAgents, setFilteredAgents] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [conformanceFilter, setConformanceFilter] = useState('all'); // 'all', 'standard', 'non-standard'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [stats, setStats] = useState(null);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Close inspection on Escape
      if (e.key === 'Escape') {
        setSelectedAgent(null);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Load data from API (with fallback to static registry)
  useEffect(() => {
    const loadData = async () => {
      console.log('[A2A] Starting data load...');
      try {
        // Try new API first
        console.log('[A2A] Fetching from API...');
        const data = await api.getAgents({ limit: 1000 });
        console.log('[A2A] API response:', data);
        const agentList = data.agents || [];
        console.log('[A2A] Loaded', agentList.length, 'agents from API');
        setAgents(agentList);
        setFilteredAgents(agentList);
        setLoading(false);

        // Load stats
        try {
          const statsData = await api.getStats();
          console.log('[A2A] Stats loaded:', statsData);
          setStats(statsData);
        } catch (statsErr) {
          console.warn('[A2A] Failed to load stats:', statsErr);
        }
      } catch (err) {
        console.warn('[A2A] API failed, falling back to static registry:', err);
        // Fallback to static registry.json
        try {
          const data = await fetchStaticRegistry();
          const agentList = data.agents || [];
          console.log('[A2A] Loaded', agentList.length, 'agents from static registry');
          setAgents(agentList);
          setFilteredAgents(agentList);
          setLoading(false);
        } catch (fallbackErr) {
          console.error('[A2A] Failed to load registry:', fallbackErr);
          setError('Failed to load agent registry');
          setLoading(false);
        }
      }
    };

    loadData();
  }, []);

  // URL Synchronization
  useEffect(() => {
    // 1. Handle initial load from URL
    if (!loading && agents.length > 0) {
      const params = new URLSearchParams(window.location.search);
      const agentId = params.get('agent');
      if (agentId && !selectedAgent) {
        const found = agents.find(a => a.name.toLowerCase().replace(/\s+/g, '-') === agentId);
        if (found) setSelectedAgent(found);
      }
    }
  }, [loading, agents]);

  useEffect(() => {
    // 2. Update URL when selection changes
    const params = new URLSearchParams(window.location.search);
    if (selectedAgent) {
      const agentId = selectedAgent.name.toLowerCase().replace(/\s+/g, '-');
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

  // Handle browser back/forward
  useEffect(() => {
    const handlePopState = () => {
      const params = new URLSearchParams(window.location.search);
      const agentId = params.get('agent');
      if (agentId) {
        const found = agents.find(a => a.name.toLowerCase().replace(/\s+/g, '-') === agentId);
        if (found) setSelectedAgent(found);
      } else {
        setSelectedAgent(null);
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [agents]);

  // Filtering Logic
  useEffect(() => {
    console.log('[A2A] Filtering - agents count:', agents.length);
    console.log('[A2A] Filtering - searchTerm:', searchTerm);
    console.log('[A2A] Filtering - selectedSkills:', selectedSkills);
    console.log('[A2A] Filtering - conformanceFilter:', conformanceFilter);

    let filtered = agents.filter(agent =>
      agent.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      agent.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (agent.author && agent.author.toLowerCase().includes(searchTerm.toLowerCase())) ||
      agent.skills.some(skill =>
        skill.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        skill.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
      )
    );

    console.log('[A2A] After text filter:', filtered.length);

    // Track search
    if (searchTerm) {
      trackSearch(searchTerm, filtered.length);
    }

    if (selectedSkills.length > 0) {
      filtered = filtered.filter(agent =>
        agent.skills.some(skill =>
          skill.tags.some(tag => selectedSkills.includes(tag))
        )
      );
      console.log('[A2A] After skill filter:', filtered.length);
    }

    // Apply conformance filter
    if (conformanceFilter === 'standard') {
      filtered = filtered.filter(agent => agent.conformance !== false);
      console.log('[A2A] After standard conformance filter:', filtered.length);
    } else if (conformanceFilter === 'non-standard') {
      filtered = filtered.filter(agent => agent.conformance === false);
      console.log('[A2A] After non-standard conformance filter:', filtered.length);
    }

    console.log('[A2A] Final filtered count:', filtered.length);
    setFilteredAgents(filtered);
  }, [searchTerm, selectedSkills, conformanceFilter, agents]);

  // Extract all tags for filter list
  const allTags = useMemo(() => {
    // Filter agents first based on conformance filter for relevant tags
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

      // Track filter change
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
      if (e.target.tagName === 'A' && e.target.pathname === '/submit') {
        e.preventDefault();
        setCurrentPage('submit');
      }
    };

    document.addEventListener('click', handleNavigate);
    return () => document.removeEventListener('click', handleNavigate);
  }, []);

  if (currentPage === 'submit') {
    return <Submit />;
  }

  console.log('[A2A] Render - loading:', loading, 'agents:', agents.length, 'filteredAgents:', filteredAgents.length);

  return (
    <Layout
      searchTerm={searchTerm}
      setSearchTerm={setSearchTerm}
      agentCount={filteredAgents.length}
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
        agents={filteredAgents}
        loading={loading}
        error={error}
        selectedAgent={selectedAgent}
        onAgentSelect={handleAgentSelect}
        onClearFilters={() => {
          setSearchTerm('');
          setSelectedSkills([]);
          setConformanceFilter('all');
        }}
      />
    </Layout>
  );
};

export default A2ARegistry;
