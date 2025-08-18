import React, { useState, useEffect, lazy, Suspense, useMemo, useCallback } from 'react';
import { Search, ExternalLink, Zap, Globe, CheckCircle, Github, Code, Copy, Check, X } from 'lucide-react';

// Lazy load non-critical components
const FAQ = lazy(() => import('./components/FAQ'));
const IntegrationGuide = lazy(() => import('./components/IntegrationGuide'));

const A2ARegistry = () => {
  const [agents, setAgents] = useState([]);
  const [filteredAgents, setFilteredAgents] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [copied, setCopied] = useState(false);

  // Load real data from registry.json with optimized fetching
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

    setFilteredAgents(filtered);
  }, [searchTerm, selectedSkills, agents]);

  const allTags = useMemo(() => 
    [...new Set(agents.flatMap(agent => 
      agent.skills.flatMap(skill => skill.tags || [])
    ))].sort(), [agents]
  );

  const toggleSkillFilter = useCallback((tag) => {
    setSelectedSkills(prev => 
      prev.includes(tag) 
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  }, []);

  const generateCodeSnippets = (agent) => {
    return {
      registry: `# Install the A2A Registry Python client
pip install a2a-registry-client

# Basic usage - find and connect to ${agent.name}
from a2a_registry import Registry
import requests

registry = Registry()
agent = registry.get_by_id("${agent.name.toLowerCase().replace(/\s+/g, '-')}")
print(f"Found: {agent.name} - {agent.description}")

# Connect to the agent using URL from registry
response = requests.post(agent.url, json={
    "jsonrpc": "2.0",
    "method": "hello",
    "params": {},
    "id": 1
})
print(response.json())`,

      a2a_official: `# Install the official A2A Python SDK
pip install a2a-sdk

# Using official A2A SDK to interact with ${agent.name}
import asyncio
import httpx
from uuid import uuid4
from a2a_registry import Registry
from a2a import A2ACardResolver, SendMessageRequest, MessageSendParams

async def interact_with_agent():
    # Get agent URL from registry
    registry = Registry()
    agent = registry.get_by_id("${agent.name.toLowerCase().replace(/\s+/g, '-')}")
    base_url = agent.url.rstrip('/')
    
    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=base_url
        )
        
        # Get agent capabilities
        agent_card = await resolver.resolve_card()
        print(f"Agent: {agent_card.name}")
        
        # Send a message to the agent
        send_message_payload = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'Hello! Can you help me?'}
                ],
                'messageId': uuid4().hex,
            }
        }
        
        request = SendMessageRequest(
            id=str(uuid4()), 
            params=MessageSendParams(**send_message_payload)
        )
        
        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))

# Run the async example
asyncio.run(interact_with_agent())`,
      
      search: `# Search for agents by capability or skill
from a2a_registry import Registry

registry = Registry()

# Search for agents with specific skills
${agent.skills.length > 0 ? `agents_with_skill = registry.find_by_skill("${agent.skills[0].id}")` : `agents = registry.search("${agent.name.split(' ')[0].toLowerCase()}")`}
print(f"Found {len(agents)} agents")

# Find agents by capability
streaming_agents = registry.find_by_capability("streaming")
print(f"Streaming agents: {len(streaming_agents)}")`,

      advanced: `# Advanced filtering and async usage
from a2a_registry import Registry, AsyncRegistry
import asyncio

# Synchronous filtering
registry = Registry()
filtered_agents = registry.filter_agents(
    ${agent.skills.length > 0 ? `skills=["${agent.skills[0].id}"],` : ''}
    input_modes=["text/plain"],
    capabilities=["streaming"] if ${agent.capabilities?.streaming || false} else []
)

# Async usage for high-performance applications
async def async_example():
    async with AsyncRegistry() as registry:
        agents = await registry.get_all()
        stats = await registry.get_stats()
        print(f"Total agents: {stats['total_agents']}")

asyncio.run(async_example())`
    };
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="animate-pulse">
          <div className="w-16 h-16 bg-purple-500 rounded-full"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-white text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold mb-2">Error Loading Registry</h2>
          <p className="text-purple-300">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="backdrop-blur-sm bg-white/10 border-b border-white/20 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 lg:py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <img src="/logo.svg" alt="A2A Logo" className="w-8 h-8 lg:w-10 lg:h-10" loading="eager" />
              <div>
                <h1 className="text-xl lg:text-2xl font-bold text-white">A2A Registry</h1>
                <p className="text-purple-200 text-xs lg:text-sm">Live Agent Directory</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="hidden sm:flex items-center space-x-4 text-sm text-purple-300">
                <span>{agents.length} agents</span>
                <span>•</span>
                <span>{allTags.length} skills</span>
              </div>
              <a
                href="https://github.com/prassanna-ravishankar/a2a-registry/blob/main/CONTRIBUTING.md"
                className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white px-3 lg:px-4 py-2 rounded-lg font-medium transition-all text-sm lg:text-base"
              >
                Submit Agent
              </a>
              <a 
                href="https://pypi.org/project/a2a-registry-client/" 
                className="flex items-center space-x-2 px-3 lg:px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors"
                title="Python Client on PyPI"
              >
                <span className="text-white text-sm lg:text-base font-mono">PyPI</span>
              </a>
              <a 
                href="https://github.com/prassanna-ravishankar/a2a-registry" 
                className="flex items-center space-x-2 px-3 lg:px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors"
              >
                <Github className="w-4 h-4 lg:w-5 lg:h-5 text-white" />
                <span className="text-white text-sm lg:text-base hidden sm:inline">GitHub</span>
              </a>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 lg:py-8">
        {/* Hero Section */}
        <section className="text-center mb-6 lg:mb-8" aria-labelledby="hero-heading">
          <h1 id="hero-heading" className="text-4xl lg:text-5xl xl:text-6xl font-bold text-white mb-4">
            Discover <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">Live AI Agents</span>
          </h1>
          <p className="text-lg lg:text-xl text-purple-200 mb-4 max-w-4xl mx-auto">
            A community-driven directory of live, hosted A2A Protocol compliant AI agents. Find, connect, and integrate with production-ready agents.
          </p>
          <div className="flex flex-wrap justify-center gap-4 lg:gap-6 text-sm text-purple-300" role="list">
            <div className="flex items-center space-x-2" role="listitem">
              <Globe className="w-4 h-4" aria-hidden="true" />
              <span>Live & Hosted</span>
            </div>
            <div className="flex items-center space-x-2" role="listitem">
              <CheckCircle className="w-4 h-4" aria-hidden="true" />
              <span>A2A Protocol Compliant</span>
            </div>
            <div className="flex items-center space-x-2" role="listitem">
              <Github className="w-4 h-4" aria-hidden="true" />
              <span>Open Source</span>
            </div>
          </div>
        </section>

        {/* Search and Filters */}
        <section className="mb-6" aria-labelledby="search-heading">
          <h2 id="search-heading" className="sr-only">Search and Filter Agents</h2>
          <div className="space-y-4">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-purple-300" aria-hidden="true" />
              <input
                type="text"
                placeholder="Search agents by name, description, or skills..."
                className="w-full pl-12 pr-4 py-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-xl text-white placeholder-purple-300 focus:outline-none focus:ring-2 focus:ring-purple-500 transition-all"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                aria-label="Search agents"
              />
            </div>

            {/* Skill Filters */}
            {allTags.length > 0 && (
              <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by skills">
                {allTags.slice(0, 15).map(tag => (
                  <button
                    key={tag}
                    onClick={() => toggleSkillFilter(tag)}
                    className={`px-3 py-1.5 rounded-full text-sm transition-all ${
                      selectedSkills.includes(tag)
                        ? 'bg-purple-500 text-white'
                        : 'bg-white/10 text-purple-200 hover:bg-white/20'
                    }`}
                    aria-pressed={selectedSkills.includes(tag)}
                  >
                    {tag}
                  </button>
                ))}
                {allTags.length > 15 && (
                  <span className="text-purple-300 text-sm px-3 py-1.5">
                    +{allTags.length - 15} more
                  </span>
                )}
              </div>
            )}
          </div>
        </section>

        {/* Agents Grid */}
        <section aria-labelledby="agents-heading">
          <h2 id="agents-heading" className="sr-only">Available A2A Agents</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4 lg:gap-6" role="list">
            {filteredAgents.map((agent, index) => (
              <article key={index} className="group bg-white/10 backdrop-blur-sm rounded-xl p-4 lg:p-5 border border-white/20 hover:bg-white/15 transition-all hover:scale-[1.02] hover:shadow-2xl" role="listitem">
                {/* Agent Header */}
                <header className="flex items-start justify-between mb-3">
                  <div className="min-w-0 flex-1">
                    <h3 className="text-lg lg:text-xl font-bold text-white mb-1 truncate">{agent.name}</h3>
                    <p className="text-purple-300 text-xs lg:text-sm truncate">
                      v{agent.version} • {agent.author || agent.provider?.organization || 'Unknown'}
                    </p>
                  </div>
                  <div className="flex space-x-1.5 ml-2" aria-label="Agent capabilities">
                    {agent.capabilities?.streaming && (
                      <div className="w-2 h-2 bg-green-400 rounded-full" title="Streaming enabled" aria-label="Streaming enabled"></div>
                    )}
                    {agent.capabilities?.pushNotifications && (
                      <div className="w-2 h-2 bg-blue-400 rounded-full" title="Push notifications enabled" aria-label="Push notifications enabled"></div>
                    )}
                  </div>
                </header>

                {/* Description */}
                <p className="text-purple-100 mb-3 text-xs lg:text-sm leading-relaxed line-clamp-3">
                  {agent.description}
                </p>

                {/* Skills */}
                <section className="mb-3">
                  <h4 className="text-white font-semibold text-xs lg:text-sm mb-2">Skills</h4>
                  <div className="space-y-2">
                    {agent.skills.slice(0, 2).map((skill, skillIndex) => (
                      <div key={skillIndex} className="bg-white/5 rounded-lg p-2.5">
                        <div className="font-medium text-white text-xs lg:text-sm truncate">{skill.name}</div>
                        <div className="text-purple-200 text-xs mb-1.5 line-clamp-2">{skill.description}</div>
                        <div className="flex flex-wrap gap-1">
                          {(skill.tags || []).slice(0, 3).map((tag, tagIndex) => (
                            <span key={tagIndex} className="px-1.5 py-0.5 bg-purple-500/30 text-purple-200 rounded text-xs">
                              {tag}
                            </span>
                          ))}
                          {skill.tags && skill.tags.length > 3 && (
                            <span className="text-purple-300 text-xs">+{skill.tags.length - 3}</span>
                          )}
                        </div>
                      </div>
                    ))}
                    {agent.skills.length > 2 && (
                      <div className="text-purple-300 text-xs">
                        +{agent.skills.length - 2} more skills
                      </div>
                    )}
                  </div>
                </section>

                {/* Actions */}
                <footer className="flex space-x-2">
                  <a
                    href={agent.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white py-2 px-3 rounded-lg text-xs lg:text-sm font-medium flex items-center justify-center space-x-1.5 transition-all"
                    aria-label={`Connect to ${agent.name}`}
                  >
                    <ExternalLink className="w-3.5 h-3.5 lg:w-4 lg:h-4" aria-hidden="true" />
                    <span>Connect</span>
                  </a>
                  <button
                    onClick={() => setSelectedAgent(agent)}
                    className="bg-white/10 hover:bg-white/20 text-purple-200 py-2 px-3 rounded-lg transition-all"
                    title="View Code Examples"
                    aria-label={`View code examples for ${agent.name}`}
                  >
                    <Code className="w-3.5 h-3.5 lg:w-4 lg:h-4" aria-hidden="true" />
                  </button>
                  <a
                    href={agent.wellKnownURI}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="bg-white/10 hover:bg-white/20 text-purple-200 py-2 px-3 rounded-lg transition-all"
                    title="View Agent Card"
                    aria-label={`View agent card for ${agent.name}`}
                  >
                    <Globe className="w-3.5 h-3.5 lg:w-4 lg:h-4" aria-hidden="true" />
                  </a>
                </footer>
              </article>
            ))}
          </div>

          {filteredAgents.length === 0 && !loading && (
            <div className="text-center py-16">
              <div className="text-6xl mb-4" role="img" aria-label="Robot emoji">🤖</div>
              <h3 className="text-2xl font-bold text-white mb-2">No agents found</h3>
              <p className="text-purple-300">Try adjusting your search terms or filters</p>
            </div>
          )}
        </section>


        {/* Lazy-loaded FAQ and Integration Guide */}
        <Suspense fallback={
          <div className="mt-12 lg:mt-16 text-center">
            <div className="animate-pulse">
              <div className="h-8 bg-white/10 rounded w-64 mx-auto mb-4"></div>
              <div className="h-4 bg-white/5 rounded w-96 mx-auto"></div>
            </div>
          </div>
        }>
          <FAQ />
        </Suspense>

        <Suspense fallback={
          <div className="mt-12 lg:mt-16 text-center">
            <div className="animate-pulse">
              <div className="h-8 bg-white/10 rounded w-64 mx-auto mb-4"></div>
              <div className="h-4 bg-white/5 rounded w-96 mx-auto"></div>
            </div>
          </div>
        }>
          <IntegrationGuide />
        </Suspense>

        {/* Footer */}
        <footer className="mt-12 lg:mt-16 pt-6 lg:pt-8 border-t border-white/20">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            <div className="text-center md:text-left">
              <p className="text-purple-300 mb-2">
                Built with ❤️ by the A2A community
              </p>
            </div>
            <div className="flex justify-center md:justify-end space-x-6 text-sm text-purple-300">
              <a href="https://a2a-protocol.org" className="hover:text-white transition-colors">
                A2A Protocol
              </a>
              <a href="https://github.com/prassanna-ravishankar/a2a-registry/issues" className="hover:text-white transition-colors">
                Issues
              </a>
              <a href="https://github.com/prassanna-ravishankar/a2a-registry/discussions" className="hover:text-white transition-colors">
                Discussions
              </a>
            </div>
          </div>
        </footer>
      </main>

      {/* Code Snippet Modal */}
      {selectedAgent && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 rounded-xl border border-white/20 w-full max-w-4xl max-h-[90vh] overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-white/20">
              <div>
                <h3 className="text-xl font-bold text-white">{selectedAgent.name}</h3>
                <p className="text-purple-300 text-sm">Python Code Examples</p>
              </div>
              <button
                onClick={() => setSelectedAgent(null)}
                className="text-purple-300 hover:text-white transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto max-h-[70vh]">
              <div className="space-y-6">
                {/* Registry Client Usage */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-lg font-semibold text-white">Registry Client Usage</h4>
                    <button
                      onClick={() => copyToClipboard(generateCodeSnippets(selectedAgent).registry)}
                      className="flex items-center space-x-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-purple-200 transition-colors"
                    >
                      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      <span>{copied ? 'Copied!' : 'Copy'}</span>
                    </button>
                  </div>
                  <pre className="bg-black/30 rounded-lg p-4 overflow-x-auto">
                    <code className="text-green-300 text-sm">{generateCodeSnippets(selectedAgent).registry}</code>
                  </pre>
                </div>

                {/* Official A2A SDK */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-lg font-semibold text-white">Official A2A SDK</h4>
                    <button
                      onClick={() => copyToClipboard(generateCodeSnippets(selectedAgent).a2a_official)}
                      className="flex items-center space-x-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-purple-200 transition-colors"
                    >
                      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      <span>{copied ? 'Copied!' : 'Copy'}</span>
                    </button>
                  </div>
                  <pre className="bg-black/30 rounded-lg p-4 overflow-x-auto">
                    <code className="text-green-300 text-sm">{generateCodeSnippets(selectedAgent).a2a_official}</code>
                  </pre>
                </div>

                {/* Search & Discovery */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-lg font-semibold text-white">Search & Discovery</h4>
                    <button
                      onClick={() => copyToClipboard(generateCodeSnippets(selectedAgent).search)}
                      className="flex items-center space-x-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-purple-200 transition-colors"
                    >
                      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      <span>{copied ? 'Copied!' : 'Copy'}</span>
                    </button>
                  </div>
                  <pre className="bg-black/30 rounded-lg p-4 overflow-x-auto">
                    <code className="text-green-300 text-sm">{generateCodeSnippets(selectedAgent).search}</code>
                  </pre>
                </div>

                {/* Advanced Usage */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-lg font-semibold text-white">Advanced Usage</h4>
                    <button
                      onClick={() => copyToClipboard(generateCodeSnippets(selectedAgent).advanced)}
                      className="flex items-center space-x-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-purple-200 transition-colors"
                    >
                      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      <span>{copied ? 'Copied!' : 'Copy'}</span>
                    </button>
                  </div>
                  <pre className="bg-black/30 rounded-lg p-4 overflow-x-auto">
                    <code className="text-green-300 text-sm">{generateCodeSnippets(selectedAgent).advanced}</code>
                  </pre>
                </div>

                {/* Installation Instructions */}
                <div className="mt-6 p-4 bg-purple-900/30 rounded-lg border border-purple-500/30">
                  <h4 className="text-white font-semibold mb-2">📦 Installation</h4>
                  <p className="text-purple-200 text-sm mb-2">Install the A2A Registry Python client:</p>
                  <pre className="bg-black/30 rounded p-2 text-green-300 text-sm mb-2">pip install a2a-registry-client</pre>
                  <p className="text-purple-200 text-sm mb-2">Install the official A2A Protocol SDK:</p>
                  <pre className="bg-black/30 rounded p-2 text-green-300 text-sm mb-2">pip install a2a-sdk</pre>
                  <p className="text-purple-200 text-sm">For async support:</p>
                  <pre className="bg-black/30 rounded p-2 text-green-300 text-sm">pip install a2a-registry-client[async]</pre>
                </div>

                {/* Agent Details */}
                <div className="mt-6 p-4 bg-blue-900/30 rounded-lg border border-blue-500/30">
                  <h4 className="text-white font-semibold mb-2">🤖 Agent Details</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-blue-200">URL:</span>
                      <span className="text-white ml-2">{selectedAgent.url}</span>
                    </div>
                    <div>
                      <span className="text-blue-200">Version:</span>
                      <span className="text-white ml-2">{selectedAgent.version}</span>
                    </div>
                    <div>
                      <span className="text-blue-200">Protocol:</span>
                      <span className="text-white ml-2">{selectedAgent.protocolVersion}</span>
                    </div>
                    <div>
                      <span className="text-blue-200">Author:</span>
                      <span className="text-white ml-2">{selectedAgent.author}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default A2ARegistry;