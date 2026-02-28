import React, { useState } from 'react';
import { X, Globe, FileText, Zap, Flag } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Terminal from './Terminal';
import { api } from '@/lib/api';

const REPORT_REASONS = ['spam', 'harmful', 'impersonation', 'other'];

const ReportModal = ({ agent, onClose }) => {
    const [reason, setReason] = useState('other');
    const [details, setDetails] = useState('');
    const [status, setStatus] = useState(null); // null | 'submitting' | 'done' | 'error'

    const submit = async () => {
        setStatus('submitting');
        try {
            await api.flagAgent(agent.id, reason, details);
            setStatus('done');
        } catch {
            setStatus('error');
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" onClick={onClose}>
            <div className="bg-zinc-950 border border-zinc-700 p-6 w-full max-w-sm font-mono" onClick={e => e.stopPropagation()}>
                <div className="flex items-center justify-between mb-4">
                    <span className="text-xs font-bold text-red-400 uppercase tracking-widest">Report Agent</span>
                    <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200"><X className="w-4 h-4" /></button>
                </div>
                {status === 'done' ? (
                    <p className="text-xs text-emerald-400">Report submitted. Thank you.</p>
                ) : (
                    <>
                        <p className="text-xs text-zinc-400 mb-4">Reporting: <span className="text-zinc-200">{agent.name}</span></p>
                        <div className="mb-3">
                            <label className="text-[10px] text-zinc-500 uppercase block mb-1">Reason</label>
                            <select
                                value={reason}
                                onChange={e => setReason(e.target.value)}
                                className="w-full bg-zinc-900 border border-zinc-700 text-zinc-300 text-xs px-2 py-1.5"
                            >
                                {REPORT_REASONS.map(r => (
                                    <option key={r} value={r}>{r}</option>
                                ))}
                            </select>
                        </div>
                        <div className="mb-4">
                            <label className="text-[10px] text-zinc-500 uppercase block mb-1">Details (optional)</label>
                            <textarea
                                value={details}
                                onChange={e => setDetails(e.target.value)}
                                rows={3}
                                className="w-full bg-zinc-900 border border-zinc-700 text-zinc-300 text-xs px-2 py-1.5 resize-none"
                                placeholder="Describe the issue..."
                            />
                        </div>
                        {status === 'error' && <p className="text-xs text-red-400 mb-2">Submission failed. Try again.</p>}
                        <Button
                            onClick={submit}
                            disabled={status === 'submitting'}
                            className="w-full bg-red-900 hover:bg-red-800 text-red-100 text-xs font-mono uppercase tracking-wider rounded-none"
                        >
                            {status === 'submitting' ? 'Submitting...' : 'Submit Report'}
                        </Button>
                    </>
                )}
            </div>
        </div>
    );
};

const InspectionDeck = ({ agent, onClose }) => {
    const [showReport, setShowReport] = useState(false);

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
        <>
        {showReport && <ReportModal agent={agent} onClose={() => setShowReport(false)} />}
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
                                        {`from a2a_registry import APIRegistry

registry = APIRegistry()
agent = registry.get_by_id("${agent.id}")
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
            <div className="p-4 border-t border-zinc-800 bg-zinc-900/30 space-y-2">
                <div className="grid grid-cols-2 gap-3">
                    <Button className="bg-zinc-100 hover:bg-white text-black font-mono font-bold text-xs uppercase tracking-wider rounded-none" asChild>
                        <a href={agent.url} target="_blank" rel="noopener noreferrer">
                            <Globe className="w-3 h-3 mr-2" />
                            Launch Interface
                        </a>
                    </Button>
                    {agent.documentationUrl ? (
                        <Button variant="outline" className="border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-zinc-100 font-mono text-xs uppercase tracking-wider rounded-none bg-transparent" asChild>
                            <a href={agent.documentationUrl} target="_blank" rel="noopener noreferrer">
                                <FileText className="w-3 h-3 mr-2" />
                                Documentation
                            </a>
                        </Button>
                    ) : (
                        <Button variant="outline" disabled className="border-zinc-800 text-zinc-600 font-mono text-xs uppercase tracking-wider rounded-none bg-transparent cursor-not-allowed">
                            <FileText className="w-3 h-3 mr-2" />
                            Documentation
                        </Button>
                    )}
                </div>
                <Button
                    variant="ghost"
                    onClick={() => setShowReport(true)}
                    className="w-full text-zinc-600 hover:text-red-400 hover:bg-transparent font-mono text-[10px] uppercase tracking-widest rounded-none"
                >
                    <Flag className="w-3 h-3 mr-1" />
                    Report this agent
                </Button>
            </div>
        </aside>
        </>
    );
};

export default InspectionDeck;
