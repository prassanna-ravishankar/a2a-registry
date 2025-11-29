import React, { useState, useEffect, useMemo, useCallback } from 'react';
import Layout from './components/Layout';
import AgentGrid from './components/AgentGrid';

const A2ARegistry = () => {
  const [agents, setAgents] = useState([]);
  const [filteredAgents, setFilteredAgents] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [conformanceFilter, setConformanceFilter] = useState('standard'); // 'all', 'standard', 'non-standard'
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);

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

  // Load real data from registry.json
  useEffect(() => {
    const controller = new AbortController();

    fetch('/registry.json', {
      signal: controller.signal,
      cache: 'force-cache'
    })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        const agentList = data.agents || [];
        setAgents(agentList);
        setFilteredAgents(agentList);
        setLoading(false);
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Failed to load registry:', err);
          setError('Failed to load agent registry');
          setLoading(false);
        }
      });

    return () => controller.abort();
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
        const newUrl = params.toString() ? `?${params.toString()}` : '/';
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

    // Apply conformance filter
    if (conformanceFilter === 'standard') {
      filtered = filtered.filter(agent => agent.conformance !== false);
    } else if (conformanceFilter === 'non-standard') {
      filtered = filtered.filter(agent => agent.conformance === false);
    }

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
    setSelectedSkills(prev =>
      prev.includes(tag)
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  }, []);

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
    >
      <AgentGrid
        agents={filteredAgents}
        loading={loading}
        error={error}
        selectedAgent={selectedAgent}
        onAgentSelect={setSelectedAgent}
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
