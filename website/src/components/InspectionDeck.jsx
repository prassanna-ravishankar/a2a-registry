import React from 'react';
import { X, Globe, Code, FileText, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Terminal from './Terminal';

const InspectionDeck = ({ agent, onClose }) => {
    if (!agent) {
        return (
            <aside className="w-full h-full border-l border-zinc-800 bg-zinc-950 flex flex-col items-center justify-center text-zinc-700">
                <div className="w-16 h-16 border-2 border-zinc-800 rounded-full flex items-center justify-center mb-4">
                    <Zap className="w-6 h-6" />
                </div>
                <p className="font-mono text-xs uppercase tracking-widest">No Agent Selected</p>
                <p className="font-mono text-[10px] mt-2">Select an agent from the grid to inspect</p>
            </aside>
        );
    }

    return (
        <aside className="w-full h-full border-l border-zinc-800 bg-zinc-950 flex flex-col">
            {/* Header */}
            <div className="h-12 border-b border-zinc-800 flex items-center justify-between px-4 bg-zinc-900/30">
                <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-emerald-500 animate-pulse" />
                    <span className="text-xs font-mono font-bold text-emerald-500 tracking-wider">INSPECTION_DECK</span>
                </div>
                <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-500 hover:text-zinc-200" onClick={onClose}>
                    <X className="w-4 h-4" />
                </Button>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar">
                <div className="p-6 space-y-8">
                    {/* Agent Identity */}
                    <div>
                        <h2 className="text-xl font-mono font-bold text-zinc-100 mb-1">{agent.name}</h2>
                        <div className="flex items-center gap-3 text-xs font-mono text-zinc-500 mb-4">
                            <span className="px-1.5 py-0.5 bg-zinc-900 border border-zinc-800 text-zinc-400">v{agent.version}</span>
                            <span>ID: {agent.name.toLowerCase().replace(/\s+/g, '-')}</span>
                        </div>
                        <p className="text-sm text-zinc-400 font-mono leading-relaxed border-l-2 border-zinc-800 pl-4">
                            {agent.description}
                        </p>
                    </div>

                    {/* Connection Interface */}
                    <div className="border border-zinc-800 bg-black h-64">
                        <Terminal agent={agent} />
                    </div>

                    {/* Technical Specs */}
                    <div className="space-y-4">
                        <h3 className="text-xs font-mono font-bold text-zinc-500 uppercase tracking-widest border-b border-zinc-800 pb-2">Technical Specifications</h3>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-1">
                                <div className="text-[10px] text-zinc-600 font-mono uppercase">Provider</div>
                                <div className="text-sm text-zinc-300 font-mono">{agent.author || agent.provider?.organization || 'Unknown'}</div>
                            </div>
                            <div className="space-y-1">
                                <div className="text-[10px] text-zinc-600 font-mono uppercase">License</div>
                                <div className="text-sm text-zinc-300 font-mono">{agent.license || 'MIT'}</div>
                            </div>
                            <div className="space-y-1">
                                <div className="text-[10px] text-zinc-600 font-mono uppercase">Capabilities</div>
                                <div className="flex gap-2">
                                    {agent.capabilities?.streaming && <span className="text-xs text-emerald-500 font-mono">[STREAMING]</span>}
                                    {agent.capabilities?.pushNotifications && <span className="text-xs text-blue-500 font-mono">[PUSH]</span>}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Integration Snippets */}
                    <div className="space-y-4">
                        <h3 className="text-xs font-mono font-bold text-zinc-500 uppercase tracking-widest border-b border-zinc-800 pb-2">Integration</h3>
                        <Tabs defaultValue="registry" className="w-full">
                            <TabsList className="w-full bg-zinc-900/50 border border-zinc-800 p-0 h-8">
                                <TabsTrigger value="registry" className="flex-1 text-[10px] font-mono h-full data-[state=active]:bg-zinc-800 data-[state=active]:text-emerald-400">REGISTRY</TabsTrigger>
                                <TabsTrigger value="sdk" className="flex-1 text-[10px] font-mono h-full data-[state=active]:bg-zinc-800 data-[state=active]:text-emerald-400">SDK</TabsTrigger>
                                <TabsTrigger value="curl" className="flex-1 text-[10px] font-mono h-full data-[state=active]:bg-zinc-800 data-[state=active]:text-emerald-400">CURL</TabsTrigger>
                            </TabsList>
                            <div className="mt-2">
                                <TabsContent value="registry">
                                    <pre className="bg-zinc-950 p-3 border border-zinc-800 font-mono text-[10px] text-zinc-400 overflow-x-auto custom-scrollbar">
                                        {`from a2a_registry import Registry

registry = Registry()
agent = registry.get_by_id("${agent.name.toLowerCase().replace(/\\s+/g, '-')}")
print(f"Found: {agent.name}")

# Connect
client = agent.connect()`}
                                    </pre>
                                </TabsContent>
                                <TabsContent value="sdk">
                                    <pre className="bg-zinc-950 p-3 border border-zinc-800 font-mono text-[10px] text-zinc-400 overflow-x-auto custom-scrollbar">
                                        {`import asyncio
from a2a import A2ACardResolver

async def main():
    resolver = A2ACardResolver(base_url="${agent.url}")
    card = await resolver.resolve_card()
    print(f"Connected to {card.name}")

asyncio.run(main())`}
                                    </pre>
                                </TabsContent>
                                <TabsContent value="curl">
                                    <pre className="bg-zinc-950 p-3 border border-zinc-800 font-mono text-[10px] text-zinc-400 overflow-x-auto custom-scrollbar">
                                        {`curl -X POST ${agent.url} \\
  -H "Content-Type: application/json" \\
  -d '{
    "jsonrpc": "2.0",
    "method": "hello",
    "params": {},
    "id": 1
  }'`}
                                    </pre>
                                </TabsContent>
                            </div>
                        </Tabs>
                    </div>
                </div>
            </div>

            {/* Footer Actions */}
            <div className="p-4 border-t border-zinc-800 bg-zinc-900/30 grid grid-cols-2 gap-3">
                <Button className="bg-zinc-100 hover:bg-white text-black font-mono font-bold text-xs uppercase tracking-wider rounded-none" asChild>
                    <a href={agent.url} target="_blank" rel="noopener noreferrer">
                        <Globe className="w-3 h-3 mr-2" />
                        Launch Interface
                    </a>
                </Button>
                <Button variant="outline" className="border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-zinc-100 font-mono text-xs uppercase tracking-wider rounded-none bg-transparent">
                    <FileText className="w-3 h-3 mr-2" />
                    Documentation
                </Button>
            </div>
        </aside>
    );
};

export default InspectionDeck;
