import React, { useState, useEffect, lazy, Suspense, useMemo, useCallback } from 'react';
import { Search, ExternalLink, Zap, Globe, CheckCircle, Github, Code, Copy, Check, ArrowUp, Download, Info, BookOpen, FileText, Radio } from 'lucide-react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

// Lazy load non-critical components
const FAQ = lazy(() => import('./components/FAQ'));

const A2ARegistry = () => {
  const [agents, setAgents] = useState([]);
  const [filteredAgents, setFilteredAgents] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSkills, setSelectedSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [copiedButton, setCopiedButton] = useState(null); // Track which button was copied
  const [showHelp, setShowHelp] = useState(false);
  const [showBackToTop, setShowBackToTop] = useState(false);
  const [showMCPDialog, setShowMCPDialog] = useState(false);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Focus search on '/' key
      if (e.key === '/' && !e.metaKey && !e.ctrlKey) {
        const searchInput = document.getElementById('agent-search');
        if (searchInput && document.activeElement !== searchInput) {
          e.preventDefault();
          searchInput.focus();
        }
      }
      // Show help on '?' key
      if (e.key === '?' && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        setShowHelp(true);
      }
      // Close dialogs on Escape
      if (e.key === 'Escape') {
        setShowHelp(false);
        setSelectedAgent(null);
        setShowMCPDialog(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Scroll to top button visibility
  useEffect(() => {
    const handleScroll = () => {
      setShowBackToTop(window.scrollY > 400);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

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

asyncio.run(async_example())`,

      integrated: `# Integrated Discover → Invoke workflow
# Combine registry discovery with A2A SDK invocation
from a2a_registry import Registry

# Step 1: Discover agent
registry = Registry()
agent = registry.get_by_id("${agent.registry_id || agent.name.toLowerCase().replace(/\s+/g, '-')}")

# Step 2: Connect with one line!
client = agent.connect()

# Step 3: Invoke using A2A SDK
# Now use the official A2A SDK methods:
# - client.message.send(...)
# - client.message.stream(...)
# - client.tasks.get(...)

print(f"Connected to {agent.name}")
print(f"Ready to invoke skills: {[s.id for s in agent.skills]}")`
    };
  };

  const copyToClipboard = (text, buttonId) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedButton(buttonId);
      setTimeout(() => setCopiedButton(null), 2000);
    });
  };

  if (loading) {
    return (
      <TooltipProvider>
      <div className="min-h-screen bg-gradient-to-br from-violet-50 via-purple-50 to-pink-50">
        <div className="container mx-auto px-4 sm:px-6 py-8">
          <div className="text-center mb-8">
            <div className="w-48 h-12 bg-purple-200 rounded-lg mx-auto mb-4 animate-pulse"></div>
            <div className="w-96 h-6 bg-purple-100 rounded mx-auto animate-pulse"></div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-6">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Card key={i} className="bg-white/90 flex flex-col h-full">
                <CardHeader>
                  <div className="w-32 h-6 bg-gray-200 rounded animate-pulse mb-2"></div>
                  <div className="w-24 h-4 bg-gray-100 rounded animate-pulse"></div>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col">
                  <div className="min-h-[60px] mb-4">
                    <div className="space-y-2">
                      <div className="w-full h-4 bg-gray-100 rounded animate-pulse"></div>
                      <div className="w-full h-4 bg-gray-100 rounded animate-pulse"></div>
                      <div className="w-3/4 h-4 bg-gray-100 rounded animate-pulse"></div>
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="w-16 h-4 bg-gray-200 rounded animate-pulse mb-2"></div>
                    <div className="space-y-2">
                      <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-2.5 border border-purple-100">
                        <div className="w-32 h-4 bg-gray-200 rounded animate-pulse mb-1"></div>
                        <div className="w-full h-3 bg-gray-100 rounded animate-pulse"></div>
                      </div>
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="flex gap-2 pt-4">
                  <div className="flex-1 h-9 bg-purple-200 rounded animate-pulse"></div>
                  <div className="flex-1 h-9 bg-gray-200 rounded animate-pulse"></div>
                </CardFooter>
              </Card>
            ))}
          </div>
        </div>
      </div>
      </TooltipProvider>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold mb-2">Error Loading Registry</h2>
          <p className="text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <TooltipProvider>
    <div className="min-h-screen bg-gradient-to-br from-violet-50 via-purple-50 to-pink-50">
      {/* Background decoration */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-0 -left-4 w-72 h-72 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob"></div>
        <div className="absolute top-0 -right-4 w-72 h-72 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-8 left-20 w-72 h-72 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-70 animate-blob animation-delay-4000"></div>
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 w-full border-b bg-white/80 backdrop-blur-xl supports-[backdrop-filter]:bg-white/60">
        <div className="container mx-auto px-4 sm:px-6 py-3 lg:py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <img src="/logo.svg" alt="A2A Logo" className="w-8 h-8 lg:w-10 lg:h-10" loading="eager" />
              <div>
                <h1 className="text-xl lg:text-2xl font-bold">A2A Registry</h1>
                <p className="text-muted-foreground text-xs lg:text-sm">Live Agent Directory</p>
              </div>
            </div>
            <div className="flex items-center gap-2 lg:gap-3">
              <div className="hidden sm:flex items-center gap-4 text-sm text-muted-foreground">
                <span>{agents.length} agents</span>
                <span>•</span>
                <span>{allTags.length} skills</span>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="icon"
                    className="border-purple-200 hover:bg-purple-50"
                    onClick={() => {
                      const dataStr = JSON.stringify({ agents }, null, 2);
                      const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
                      const link = document.createElement('a');
                      link.setAttribute('href', dataUri);
                      link.setAttribute('download', 'a2a-registry.json');
                      document.body.appendChild(link);
                      link.click();
                      link.remove();
                    }}
                  >
                    <Download className="w-4 h-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Export registry as JSON</p>
                </TooltipContent>
              </Tooltip>
              <Button asChild size="sm" className="lg:size-default bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white border-0">
                <a href="https://github.com/prassanna-ravishankar/a2a-registry/blob/main/CONTRIBUTING.md">
                  Submit Agent
                </a>
              </Button>
              <Button variant="outline" size="sm" className="lg:size-default border-purple-200 hover:bg-purple-50" asChild>
                <a href="https://pypi.org/project/a2a-registry-client/" className="flex items-center gap-2">
                  <Code className="w-4 h-4" />
                  <span className="hidden sm:inline">PyPI</span>
                </a>
              </Button>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    className="lg:size-default border-purple-200 hover:bg-purple-50 flex items-center gap-2"
                    onClick={() => setShowMCPDialog(true)}
                  >
                    <Radio className="w-4 h-4" />
                    <span className="hidden sm:inline">MCP</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Model Context Protocol integration</p>
                </TooltipContent>
              </Tooltip>
              <Button variant="outline" size="icon" className="border-purple-200 hover:bg-purple-50" asChild>
                <a href="https://github.com/prassanna-ravishankar/a2a-registry">
                  <Github className="w-4 h-4" />
                </a>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 sm:px-6 py-6 lg:py-8 max-w-7xl">
        {/* Hero Section */}
        <section className="text-center mb-8 lg:mb-12">
          <h1 className="text-4xl lg:text-5xl xl:text-6xl font-bold mb-4">
            Discover <span className="bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">Live AI Agents</span>
          </h1>
          <p className="text-lg lg:text-xl text-muted-foreground mb-6 max-w-3xl mx-auto">
            A community-driven directory of live, hosted A2A Protocol compliant AI agents. Find, connect, and integrate with production-ready agents.
          </p>
          <div className="flex flex-wrap justify-center gap-6 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 flex-shrink-0" />
              <span>Live & Hosted</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 flex-shrink-0" />
              <span>A2A Protocol Compliant</span>
            </div>
            <div className="flex items-center gap-2">
              <Github className="w-4 h-4 flex-shrink-0" />
              <span>Open Source</span>
            </div>
          </div>
        </section>

        <Separator className="mb-8" />

        {/* Search and Filters - Sticky */}
        <section className="sticky top-[65px] lg:top-[73px] z-40 bg-gradient-to-br from-violet-50/95 via-purple-50/95 to-pink-50/95 backdrop-blur-lg py-4 -mx-4 sm:-mx-6 px-4 sm:px-6 mb-8 border-b border-purple-100">
          <div className="space-y-4">
            <div className="relative max-w-2xl mx-auto">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
              <Input
                type="text"
                placeholder="Search agents by name, description, or skills..."
                className="pl-10 border-purple-200 focus:border-purple-400 bg-white/80 backdrop-blur-sm"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                id="agent-search"
              />
            </div>

            {/* Skill Filters */}
            {allTags.length > 0 && (
              <div className="flex flex-wrap gap-2 justify-center">
                {allTags.slice(0, 15).map(tag => (
                  <Badge
                    key={tag}
                    variant={selectedSkills.includes(tag) ? "default" : "outline"}
                    className={`cursor-pointer transition-all ${
                      selectedSkills.includes(tag)
                        ? 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white border-0'
                        : 'border-purple-200 hover:bg-purple-50'
                    }`}
                    onClick={() => toggleSkillFilter(tag)}
                  >
                    {tag}
                  </Badge>
                ))}
                {allTags.length > 15 && (
                  <Badge variant="outline" className="opacity-60 border-purple-200">
                    +{allTags.length - 15} more
                  </Badge>
                )}
              </div>
            )}
          </div>
        </section>

        {/* Agents Grid */}
        <section>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-6">
            {filteredAgents.map((agent, index) => (
              <Card key={index} className="bg-white/90 backdrop-blur-sm hover:shadow-2xl transition-all duration-300 hover:-translate-y-1 group border-purple-100 relative flex flex-col h-full">
                {/* Status Badge */}
                {agent.status && (
                  <Badge
                    className={`absolute top-3 right-3 ${
                      agent.status === 'stable' ? 'bg-green-100 text-green-700' :
                      agent.status === 'beta' ? 'bg-yellow-100 text-yellow-700' :
                      agent.status === 'new' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }`}
                    variant="secondary"
                  >
                    {agent.status || 'stable'}
                  </Badge>
                )}
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="min-w-0 flex-1 pr-12">
                      <CardTitle className="truncate">{agent.name}</CardTitle>
                      <CardDescription className="truncate">
                        v{agent.version} • {agent.author || agent.provider?.organization || 'Unknown'}
                      </CardDescription>
                    </div>
                    <div className="flex gap-1.5 ml-2">
                      {agent.capabilities?.streaming && (
                        <Tooltip>
                          <TooltipTrigger>
                            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Streaming enabled</p>
                          </TooltipContent>
                        </Tooltip>
                      )}
                      {agent.capabilities?.pushNotifications && (
                        <Tooltip>
                          <TooltipTrigger>
                            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>Push notifications</p>
                          </TooltipContent>
                        </Tooltip>
                      )}
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="flex-1 flex flex-col">
                  <div className="min-h-[60px] mb-4">
                    <p className="text-sm text-muted-foreground line-clamp-3">
                      {agent.description}
                    </p>
                  </div>

                  {/* Skills */}
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold mb-2">Skills</h4>
                    <div className="space-y-2">
                      {agent.skills.slice(0, 2).map((skill, skillIndex) => (
                        <div key={skillIndex} className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-2.5 space-y-1.5 border border-purple-100">
                          <div className="font-medium text-sm truncate">{skill.name}</div>
                          <div className="text-xs text-muted-foreground line-clamp-2">{skill.description}</div>
                          <div className="flex flex-wrap gap-1">
                            {(skill.tags || []).slice(0, 3).map((tag, tagIndex) => (
                              <Badge key={tagIndex} variant="secondary" className="text-xs px-1.5 py-0 bg-white">
                                {tag}
                              </Badge>
                            ))}
                            {skill.tags && skill.tags.length > 3 && (
                              <span className="text-xs text-muted-foreground">+{skill.tags.length - 3}</span>
                            )}
                          </div>
                        </div>
                      ))}
                      {agent.skills.length > 2 && (
                        <div className="text-xs text-muted-foreground">
                          +{agent.skills.length - 2} more skills
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>

                <CardFooter className="flex gap-2 pt-4">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button size="sm" className="flex-1 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white" asChild>
                        <a href={agent.url} target="_blank" rel="noopener noreferrer" className="flex items-center justify-center gap-1.5">
                          <ExternalLink className="w-3.5 h-3.5" />
                          <span className="text-xs">Try Agent</span>
                        </a>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Launch agent chat interface</p>
                    </TooltipContent>
                  </Tooltip>

                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1 border-purple-200 hover:bg-purple-50 flex items-center justify-center gap-1.5"
                        onClick={() => setSelectedAgent(agent)}
                      >
                        <BookOpen className="w-3.5 h-3.5" />
                        <span className="text-xs">Documentation</span>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>View code examples and specifications</p>
                    </TooltipContent>
                  </Tooltip>
                </CardFooter>
              </Card>
            ))}
          </div>

          {filteredAgents.length === 0 && !loading && (
            <div className="text-center py-16">
              <div className="w-24 h-24 mx-auto mb-4 bg-purple-100 rounded-full flex items-center justify-center">
                <Search className="w-12 h-12 text-purple-400" />
              </div>
              <h3 className="text-2xl font-bold mb-2">No agents found</h3>
              <p className="text-muted-foreground mb-4">Try adjusting your search terms or filters</p>
              <div className="flex gap-3 justify-center">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSearchTerm('');
                    setSelectedSkills([]);
                  }}
                  className="border-purple-200 hover:bg-purple-50"
                >
                  Clear filters
                </Button>
                <Button
                  size="sm"
                  className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white"
                  asChild
                >
                  <a href="https://github.com/prassanna-ravishankar/a2a-registry/blob/main/CONTRIBUTING.md">
                    Submit an agent
                  </a>
                </Button>
              </div>
            </div>
          )}
        </section>

        {/* Lazy-loaded FAQ */}
        <Suspense fallback={<div className="mt-12 h-32 animate-pulse bg-muted/20 rounded-lg" />}>
          <FAQ />
        </Suspense>

        {/* Footer */}
        <footer className="mt-16 pt-8 border-t">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
            <div className="text-center md:text-left">
              <p className="text-muted-foreground">
                Built with ❤️ by the A2A community
              </p>
            </div>
            <div className="flex justify-center md:justify-end gap-6 text-sm text-muted-foreground">
              <a href="https://a2a-protocol.org" className="hover:text-foreground transition-colors">
                A2A Protocol
              </a>
              <a href="https://github.com/prassanna-ravishankar/a2a-registry/issues" className="hover:text-foreground transition-colors">
                Issues
              </a>
              <a href="https://github.com/prassanna-ravishankar/a2a-registry/discussions" className="hover:text-foreground transition-colors">
                Discussions
              </a>
            </div>
          </div>
        </footer>
      </main>

      {/* Back to Top Button */}
      {showBackToTop && (
        <Button
          size="icon"
          className="fixed bottom-6 right-6 z-50 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white shadow-lg"
          onClick={scrollToTop}
        >
          <ArrowUp className="w-4 h-4" />
        </Button>
      )}

      {/* MCP Integration Dialog */}
      <Dialog open={showMCPDialog} onOpenChange={setShowMCPDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Radio className="w-5 h-5" />
              MCP Integration
            </DialogTitle>
            <DialogDescription>
              Enable AI assistants like Claude to discover and query agents from the A2A Registry
            </DialogDescription>
          </DialogHeader>

          <Tabs defaultValue="claude-desktop" className="mt-4">
            <TabsList className="grid w-full grid-cols-3 lg:grid-cols-5">
              <TabsTrigger value="claude-desktop" className="text-xs">Claude Desktop</TabsTrigger>
              <TabsTrigger value="cline" className="text-xs">Cline</TabsTrigger>
              <TabsTrigger value="zed" className="text-xs">Zed</TabsTrigger>
              <TabsTrigger value="cursor" className="text-xs lg:block hidden">Cursor</TabsTrigger>
              <TabsTrigger value="other" className="text-xs lg:block hidden">Other</TabsTrigger>
            </TabsList>

            {/* Claude Desktop */}
            <TabsContent value="claude-desktop" className="space-y-4 mt-4">
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
                <h4 className="font-semibold mb-2 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-purple-600" />
                  Quick Setup
                </h4>
                <p className="text-sm text-muted-foreground mb-3">
                  The most popular way to use the A2A Registry MCP server.
                </p>
              </div>

              <div>
                <h5 className="text-sm font-semibold mb-2">1. Run the MCP Server</h5>
                <div className="relative">
                  <pre className="bg-muted rounded p-3 text-sm overflow-x-auto">uvx a2a-registry-client</pre>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="absolute top-2 right-2"
                    onClick={() => copyToClipboard('uvx a2a-registry-client', 'mcp-uvx')}
                  >
                    {copiedButton === 'mcp-uvx' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                  </Button>
                </div>
              </div>

              <div>
                <h5 className="text-sm font-semibold mb-2">2. Add to Claude Desktop Config</h5>
                <div className="bg-muted/50 rounded p-2 text-xs text-muted-foreground mb-2">
                  <strong>macOS:</strong> ~/Library/Application Support/Claude/claude_desktop_config.json<br />
                  <strong>Windows:</strong> %APPDATA%\Claude\claude_desktop_config.json
                </div>
                <div className="relative">
                  <pre className="bg-muted rounded p-3 text-xs overflow-x-auto">{`{
  "mcpServers": {
    "a2a-registry": {
      "command": "uvx",
      "args": ["a2a-registry-client"]
    }
  }
}`}</pre>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="absolute top-2 right-2"
                    onClick={() => copyToClipboard(`{
  "mcpServers": {
    "a2a-registry": {
      "command": "uvx",
      "args": ["a2a-registry-client"]
    }
  }
}`, 'mcp-config')}
                  >
                    {copiedButton === 'mcp-config' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                  </Button>
                </div>
              </div>

              <div className="bg-blue-50 rounded p-3 text-xs text-blue-900 border border-blue-200">
                <strong>After setup:</strong> Restart Claude Desktop and look for the 🔌 icon to verify MCP servers are loaded.
              </div>
            </TabsContent>

            {/* Cline (VS Code) */}
            <TabsContent value="cline" className="space-y-4 mt-4">
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
                <h4 className="font-semibold mb-2">Cline for VS Code</h4>
                <p className="text-sm text-muted-foreground">
                  Popular AI coding assistant with MCP support
                </p>
              </div>

              <div>
                <h5 className="text-sm font-semibold mb-2">Setup Steps</h5>
                <ol className="text-sm space-y-2 list-decimal list-inside">
                  <li>Install Cline extension from VS Code marketplace</li>
                  <li>Open VS Code Settings (Cmd/Ctrl + ,)</li>
                  <li>Search for "Cline: MCP Settings"</li>
                  <li>Add the configuration below</li>
                  <li>Restart VS Code</li>
                </ol>
              </div>

              <div>
                <h5 className="text-sm font-semibold mb-2">Configuration</h5>
                <div className="relative">
                  <pre className="bg-muted rounded p-3 text-xs overflow-x-auto">{`{
  "cline.mcpServers": {
    "a2a-registry": {
      "command": "uvx",
      "args": ["a2a-registry-client"]
    }
  }
}`}</pre>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="absolute top-2 right-2"
                    onClick={() => copyToClipboard(`{
  "cline.mcpServers": {
    "a2a-registry": {
      "command": "uvx",
      "args": ["a2a-registry-client"]
    }
  }
}`, 'mcp-cline')}
                  >
                    {copiedButton === 'mcp-cline' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                  </Button>
                </div>
              </div>
            </TabsContent>

            {/* Zed */}
            <TabsContent value="zed" className="space-y-4 mt-4">
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
                <h4 className="font-semibold mb-2">Zed Editor</h4>
                <p className="text-sm text-muted-foreground">
                  High-performance editor with built-in MCP support
                </p>
              </div>

              <div>
                <h5 className="text-sm font-semibold mb-2">Configuration File</h5>
                <p className="text-xs text-muted-foreground mb-2">
                  Location: <code className="bg-muted px-1 rounded">~/.config/zed/settings.json</code>
                </p>
                <div className="relative">
                  <pre className="bg-muted rounded p-3 text-xs overflow-x-auto">{`{
  "context_servers": {
    "a2a-registry": {
      "command": {
        "path": "uvx",
        "args": ["a2a-registry-client"]
      }
    }
  }
}`}</pre>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="absolute top-2 right-2"
                    onClick={() => copyToClipboard(`{
  "context_servers": {
    "a2a-registry": {
      "command": {
        "path": "uvx",
        "args": ["a2a-registry-client"]
      }
    }
  }
}`, 'mcp-zed')}
                  >
                    {copiedButton === 'mcp-zed' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                  </Button>
                </div>
              </div>

              <div className="text-xs text-muted-foreground">
                <strong>After setup:</strong> Restart Zed and the MCP server will appear in the context menu.
              </div>
            </TabsContent>

            {/* Cursor */}
            <TabsContent value="cursor" className="space-y-4 mt-4">
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
                <h4 className="font-semibold mb-2">Cursor</h4>
                <p className="text-sm text-muted-foreground">
                  AI-first code editor
                </p>
              </div>

              <div>
                <h5 className="text-sm font-semibold mb-2">Setup</h5>
                <ol className="text-sm space-y-2 list-decimal list-inside">
                  <li>Open Cursor Settings (Cmd/Ctrl + ,)</li>
                  <li>Search for "MCP" settings</li>
                  <li>Add the configuration below</li>
                  <li>Restart Cursor</li>
                </ol>
              </div>

              <div>
                <h5 className="text-sm font-semibold mb-2">Configuration</h5>
                <div className="relative">
                  <pre className="bg-muted rounded p-3 text-xs overflow-x-auto">{`{
  "mcpServers": {
    "a2a-registry": {
      "command": "uvx",
      "args": ["a2a-registry-client"]
    }
  }
}`}</pre>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="absolute top-2 right-2"
                    onClick={() => copyToClipboard(`{
  "mcpServers": {
    "a2a-registry": {
      "command": "uvx",
      "args": ["a2a-registry-client"]
    }
  }
}`, 'mcp-cursor')}
                  >
                    {copiedButton === 'mcp-cursor' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                  </Button>
                </div>
              </div>

              <div className="bg-yellow-50 rounded p-3 text-xs text-yellow-900 border border-yellow-200">
                <strong>Note:</strong> MCP support in Cursor may be in beta. Check Cursor's documentation for latest setup instructions.
              </div>
            </TabsContent>

            {/* Other Tools */}
            <TabsContent value="other" className="space-y-4 mt-4">
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
                <h4 className="font-semibold mb-2">Other Tools & Custom Integrations</h4>
                <p className="text-sm text-muted-foreground">
                  Generic configuration for any MCP-compatible tool
                </p>
              </div>

              <div>
                <h5 className="text-sm font-semibold mb-2">Supported Tools</h5>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-muted rounded p-2">• Continue (VS Code)</div>
                  <div className="bg-muted rounded p-2">• Custom MCP clients</div>
                  <div className="bg-muted rounded p-2">• Windsurf</div>
                  <div className="bg-muted rounded p-2">• And more...</div>
                </div>
              </div>

              <div>
                <h5 className="text-sm font-semibold mb-2">Generic Configuration</h5>
                <div className="relative">
                  <pre className="bg-muted rounded p-3 text-xs overflow-x-auto">{`{
  "mcpServers": {
    "a2a-registry": {
      "command": "uvx",
      "args": ["a2a-registry-client"]
    }
  }
}`}</pre>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="absolute top-2 right-2"
                    onClick={() => copyToClipboard(`{
  "mcpServers": {
    "a2a-registry": {
      "command": "uvx",
      "args": ["a2a-registry-client"]
    }
  }
}`, 'mcp-other')}
                  >
                    {copiedButton === 'mcp-other' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                  </Button>
                </div>
              </div>

              <div className="text-xs text-muted-foreground">
                <strong>Protocol:</strong> The server uses stdio transport and follows the{' '}
                <a href="https://spec.modelcontextprotocol.io/" target="_blank" rel="noopener noreferrer" className="text-purple-600 hover:underline">
                  MCP specification
                </a>
              </div>
            </TabsContent>
          </Tabs>

          <Separator className="my-6" />

          {/* What You Can Do */}
          <div className="space-y-4">
            <div>
              <h4 className="font-semibold mb-3">What You Can Do</h4>
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
                <p className="text-sm text-muted-foreground mb-2">Once configured, ask your AI assistant:</p>
                <ul className="space-y-1 text-sm">
                  <li>• "Find agents that support streaming"</li>
                  <li>• "Search for chess-playing agents"</li>
                  <li>• "Show me all agents by a specific author"</li>
                  <li>• "Which agents support JSON output?"</li>
                  <li>• "What are the registry statistics?"</li>
                </ul>
              </div>
            </div>

            {/* Available Tools Summary */}
            <div>
              <h5 className="text-sm font-semibold mb-2">Available MCP Tools</h5>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                <div className="bg-muted rounded p-2">✓ Search agents</div>
                <div className="bg-muted rounded p-2">✓ Filter by capability</div>
                <div className="bg-muted rounded p-2">✓ Filter by skill</div>
                <div className="bg-muted rounded p-2">✓ Filter by author</div>
                <div className="bg-muted rounded p-2">✓ Get agent details</div>
                <div className="bg-muted rounded p-2">✓ + 8 more tools</div>
              </div>
            </div>

            {/* Full Documentation Link */}
            <div className="flex justify-center pt-2">
              <Button
                variant="outline"
                className="border-purple-200 hover:bg-purple-50"
                asChild
              >
                <a
                  href="https://github.com/prassanna-ravishankar/a2a-registry/blob/main/MCP_INTEGRATION.md"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2"
                >
                  <BookOpen className="w-4 h-4" />
                  View Full Documentation
                  <ExternalLink className="w-3 h-3" />
                </a>
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Help Dialog */}
      <Dialog open={showHelp} onOpenChange={setShowHelp}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Keyboard Shortcuts</DialogTitle>
            <DialogDescription>Quick navigation and actions</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 mt-4">
            <div className="flex justify-between items-center py-2 px-3 bg-purple-50 rounded">
              <span className="text-sm">Focus search</span>
              <kbd className="px-2 py-1 bg-white rounded text-xs border">/</kbd>
            </div>
            <div className="flex justify-between items-center py-2 px-3 bg-purple-50 rounded">
              <span className="text-sm">Show this help</span>
              <kbd className="px-2 py-1 bg-white rounded text-xs border">?</kbd>
            </div>
            <div className="flex justify-between items-center py-2 px-3 bg-purple-50 rounded">
              <span className="text-sm">Close dialogs</span>
              <kbd className="px-2 py-1 bg-white rounded text-xs border">Esc</kbd>
            </div>
            <Separator className="my-4" />
            <p className="text-sm text-muted-foreground">
              Tip: Click any skill tag to filter agents by that skill.
            </p>
          </div>
        </DialogContent>
      </Dialog>

      {/* Code Snippet Modal */}
      <Dialog open={!!selectedAgent} onOpenChange={() => setSelectedAgent(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedAgent?.name}</DialogTitle>
            <DialogDescription className="mt-2">
              {selectedAgent?.description}
            </DialogDescription>
          </DialogHeader>

          {selectedAgent && (
            <Tabs defaultValue="getstarted" className="mt-6">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="getstarted" className="flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  Get Started
                </TabsTrigger>
                <TabsTrigger value="examples" className="flex items-center gap-2">
                  <Code className="w-4 h-4" />
                  More Examples
                </TabsTrigger>
                <TabsTrigger value="specs" className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Specifications
                </TabsTrigger>
              </TabsList>

              {/* GET STARTED TAB */}
              <TabsContent value="getstarted" className="space-y-6 mt-4">
              {/* Hero message */}
              <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
                <h4 className="font-semibold mb-2 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-purple-600" />
                  Quick Connect in 3 Lines
                </h4>
                <p className="text-sm text-muted-foreground">
                  The fastest way to discover and invoke this agent using the integrated A2A SDK.
                </p>
              </div>

              {/* Integrated Discovery + Invocation */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-semibold">Code Example</h4>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(generateCodeSnippets(selectedAgent).integrated, 'integrated')}
                    className="flex items-center gap-2"
                  >
                    {copiedButton === 'integrated' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedButton === 'integrated' ? 'Copied!' : 'Copy'}</span>
                  </Button>
                </div>
                <pre className="bg-muted rounded-lg p-4 overflow-x-auto text-xs">
                  <code>{generateCodeSnippets(selectedAgent).integrated}</code>
                </pre>
              </div>

              <Separator />

              {/* Installation Instructions */}
              <div className="bg-primary/10 rounded-lg p-4 border border-primary/20">
                <h4 className="font-semibold mb-2">📦 Installation</h4>
                <p className="text-sm text-muted-foreground mb-2">With A2A SDK integration (recommended):</p>
                <pre className="bg-muted rounded p-2 text-xs mb-3">pip install "a2a-registry-client[a2a]"</pre>

                <details className="mt-3">
                  <summary className="text-sm font-medium cursor-pointer hover:text-purple-600">Other installation options</summary>
                  <div className="mt-3 space-y-3">
                    <div>
                      <p className="text-sm text-muted-foreground mb-2">Basic installation (discovery only):</p>
                      <pre className="bg-muted rounded p-2 text-xs">pip install a2a-registry-client</pre>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground mb-2">With async support:</p>
                      <pre className="bg-muted rounded p-2 text-xs">pip install "a2a-registry-client[async]"</pre>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground mb-2">All features (A2A SDK + async):</p>
                      <pre className="bg-muted rounded p-2 text-xs">pip install "a2a-registry-client[all]"</pre>
                    </div>
                  </div>
                </details>
              </div>

              </TabsContent>

              {/* MORE EXAMPLES TAB */}
              <TabsContent value="examples" className="space-y-6 mt-4">

              {/* Registry Client Usage */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h4 className="text-sm font-semibold">Registry Client (Discovery Only)</h4>
                    <p className="text-xs text-muted-foreground mt-1">Use when you only need to find agents</p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(generateCodeSnippets(selectedAgent).registry, 'registry')}
                    className="flex items-center gap-2"
                  >
                    {copiedButton === 'registry' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedButton === 'registry' ? 'Copied!' : 'Copy'}</span>
                  </Button>
                </div>
                <pre className="bg-muted rounded-lg p-4 overflow-x-auto text-xs">
                  <code>{generateCodeSnippets(selectedAgent).registry}</code>
                </pre>
              </div>

              <Separator />

              {/* Official A2A SDK */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h4 className="text-sm font-semibold">Official A2A SDK (Low-Level)</h4>
                    <p className="text-xs text-muted-foreground mt-1">Direct A2A protocol interaction</p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(generateCodeSnippets(selectedAgent).a2a_official, 'a2a_official')}
                    className="flex items-center gap-2"
                  >
                    {copiedButton === 'a2a_official' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedButton === 'a2a_official' ? 'Copied!' : 'Copy'}</span>
                  </Button>
                </div>
                <pre className="bg-muted rounded-lg p-4 overflow-x-auto text-xs">
                  <code>{generateCodeSnippets(selectedAgent).a2a_official}</code>
                </pre>
              </div>

              <Separator />

              {/* Search & Discovery */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h4 className="text-sm font-semibold">Search & Discovery</h4>
                    <p className="text-xs text-muted-foreground mt-1">Filter agents by skills and capabilities</p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(generateCodeSnippets(selectedAgent).search, 'search')}
                    className="flex items-center gap-2"
                  >
                    {copiedButton === 'search' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedButton === 'search' ? 'Copied!' : 'Copy'}</span>
                  </Button>
                </div>
                <pre className="bg-muted rounded-lg p-4 overflow-x-auto text-xs">
                  <code>{generateCodeSnippets(selectedAgent).search}</code>
                </pre>
              </div>

              <Separator />

              {/* Advanced Usage */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h4 className="text-sm font-semibold">Advanced Filtering</h4>
                    <p className="text-xs text-muted-foreground mt-1">Multi-criteria filtering and async support</p>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(generateCodeSnippets(selectedAgent).advanced, 'advanced')}
                    className="flex items-center gap-2"
                  >
                    {copiedButton === 'advanced' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedButton === 'advanced' ? 'Copied!' : 'Copy'}</span>
                  </Button>
                </div>
                <pre className="bg-muted rounded-lg p-4 overflow-x-auto text-xs">
                  <code>{generateCodeSnippets(selectedAgent).advanced}</code>
                </pre>
              </div>

              </TabsContent>

              <TabsContent value="specs" className="space-y-6 mt-4">
                {/* Agent Overview */}
                <div className="space-y-4">
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Overview</h4>
                    <div className="bg-accent/50 rounded-lg p-4 border">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground font-medium">Agent URL:</span>
                          <div className="mt-1 font-mono text-xs bg-muted p-2 rounded break-all">{selectedAgent.url}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground font-medium">Version:</span>
                          <div className="mt-1">{selectedAgent.version}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground font-medium">Protocol Version:</span>
                          <div className="mt-1">{selectedAgent.protocolVersion}</div>
                        </div>
                        <div>
                          <span className="text-muted-foreground font-medium">Author:</span>
                          <div className="mt-1">{selectedAgent.author || selectedAgent.provider?.organization || 'Unknown'}</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Capabilities */}
                  {selectedAgent.capabilities && (
                    <div>
                      <h4 className="text-sm font-semibold mb-2">Capabilities</h4>
                      <div className="bg-accent/50 rounded-lg p-4 border">
                        <div className="flex flex-wrap gap-2">
                          {selectedAgent.capabilities.streaming && (
                            <Badge variant="secondary" className="bg-green-100 text-green-700">
                              <Zap className="w-3 h-3 mr-1" />
                              Streaming
                            </Badge>
                          )}
                          {selectedAgent.capabilities.pushNotifications && (
                            <Badge variant="secondary" className="bg-blue-100 text-blue-700">
                              Push Notifications
                            </Badge>
                          )}
                          {selectedAgent.capabilities.stateTransitionHistory && (
                            <Badge variant="secondary" className="bg-purple-100 text-purple-700">
                              State History
                            </Badge>
                          )}
                          {!selectedAgent.capabilities.streaming && !selectedAgent.capabilities.pushNotifications && !selectedAgent.capabilities.stateTransitionHistory && (
                            <span className="text-sm text-muted-foreground">No special capabilities declared</span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Skills */}
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Skills ({selectedAgent.skills?.length || 0})</h4>
                    <div className="space-y-3">
                      {selectedAgent.skills?.map((skill, idx) => (
                        <div key={idx} className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-100">
                          <h5 className="font-medium text-sm mb-1">{skill.name}</h5>
                          <p className="text-xs text-muted-foreground mb-2">{skill.description}</p>
                          <div className="flex flex-wrap gap-1">
                            {skill.tags?.map((tag, tagIdx) => (
                              <Badge key={tagIdx} variant="secondary" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Well-known URI */}
                  <div>
                    <h4 className="text-sm font-semibold mb-2">Agent Card</h4>
                    <div className="bg-accent/50 rounded-lg p-4 border">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <span className="text-muted-foreground text-sm">Specification Endpoint:</span>
                          <div className="mt-1 font-mono text-xs bg-muted p-2 rounded break-all">{selectedAgent.wellKnownURI}</div>
                        </div>
                        <Button
                          size="sm"
                          variant="outline"
                          asChild
                          className="ml-4"
                        >
                          <a href={selectedAgent.wellKnownURI} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2">
                            <ExternalLink className="w-3 h-3" />
                            View JSON
                          </a>
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>
    </div>
    </TooltipProvider>
  );
};

export default A2ARegistry;
