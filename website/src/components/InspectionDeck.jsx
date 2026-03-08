import React, { useMemo, useState } from 'react';
import Markdown from 'react-markdown';
import { X, Globe, FileText, Zap, Flag, Copy, Check, ArrowUpRight, ChevronLeft, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { safeExternalUrl } from '@/lib/utils';
import Terminal from './Terminal';
import HealthBadge from './HealthBadge';
import { api } from '@/lib/api';

const REPORT_REASONS = ['spam', 'harmful', 'impersonation', 'other'];

const ReportModal = ({ agent, onClose }) => {
    const [reason, setReason] = useState('other');
    const [details, setDetails] = useState('');
    const [status, setStatus] = useState(null);

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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4" onClick={onClose}>
            <div className="w-full max-w-sm border border-zinc-700 bg-zinc-950 p-6 font-mono" onClick={(e) => e.stopPropagation()}>
                <div className="mb-4 flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-widest text-red-400">Report Agent</span>
                    <button onClick={onClose} className="text-zinc-500 hover:text-zinc-200"><X className="h-4 w-4" /></button>
                </div>
                {status === 'done' ? (
                    <p className="text-xs text-emerald-400">Report submitted. Thank you.</p>
                ) : (
                    <>
                        <p className="mb-4 text-xs text-zinc-400">Reporting: <span className="text-zinc-200">{agent.name}</span></p>
                        <div className="mb-3">
                            <label className="mb-1 block text-[10px] uppercase text-zinc-500">Reason</label>
                            <select
                                value={reason}
                                onChange={(e) => setReason(e.target.value)}
                                className="w-full border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-300"
                            >
                                {REPORT_REASONS.map((r) => (
                                    <option key={r} value={r}>{r}</option>
                                ))}
                            </select>
                        </div>
                        <div className="mb-4">
                            <label className="mb-1 block text-[10px] uppercase text-zinc-500">Details (optional)</label>
                            <textarea
                                value={details}
                                onChange={(e) => setDetails(e.target.value)}
                                rows={3}
                                className="w-full resize-none border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-300"
                                placeholder="Describe the issue..."
                            />
                        </div>
                        {status === 'error' && <p className="mb-2 text-xs text-red-400">Submission failed. Try again.</p>}
                        <Button
                            onClick={submit}
                            disabled={status === 'submitting'}
                            className="w-full rounded-none bg-red-900 font-mono text-xs uppercase tracking-wider text-red-100 hover:bg-red-800"
                        >
                            {status === 'submitting' ? 'Submitting...' : 'Submit Report'}
                        </Button>
                    </>
                )}
            </div>
        </div>
    );
};

const CopyableField = ({ label, value }) => {
    const [copied, setCopied] = useState(false);
    const copy = () => {
        navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };

    return (
        <div className="space-y-1">
            <div className="text-[10px] uppercase tracking-[0.18em] text-zinc-600">{label}</div>
            <div className="flex items-center gap-2 border border-zinc-800 bg-zinc-900/50 px-2 py-2">
                <span className="min-w-0 flex-1 truncate text-[11px] text-zinc-400">{value}</span>
                <button onClick={copy} className="shrink-0 text-zinc-500 hover:text-zinc-200">
                    {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                </button>
            </div>
        </div>
    );
};

const MaintainerNotes = ({ notes }) => {
    if (!notes) return null;

    return (
        <section className="border border-blue-800/50 bg-blue-950/20 p-4">
            <div className="flex items-center gap-2">
                <Info className="h-3.5 w-3.5 text-blue-400" />
                <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-blue-400">Registry Maintainer Note</span>
            </div>
            <div className="mt-3 font-mono text-xs leading-relaxed text-zinc-300 prose prose-invert prose-xs max-w-none [&_a]:text-blue-400 [&_a]:underline [&_code]:bg-zinc-800 [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-zinc-300 [&_li]:my-0 [&_ol]:my-1 [&_p]:my-1 [&_ul]:my-1">
                <Markdown>{notes}</Markdown>
            </div>
        </section>
    );
};

const AgentHero = ({ agent, mobile }) => (
    <div className={`border-b border-zinc-800 ${mobile ? 'px-4 pb-5 pt-4' : 'px-6 pb-6 pt-5'}`}>
        <div className="flex flex-wrap items-center gap-2">
            <Badge
                variant="outline"
                className={`rounded-none border px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] ${
                    agent.conformance === false
                        ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                        : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                }`}
            >
                {agent.conformance === false ? 'Non-standard' : 'A2A conformant'}
            </Badge>
            {agent.capabilities?.streaming && (
                <Badge variant="outline" className="rounded-none border-cyan-500/30 bg-cyan-500/10 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-cyan-300">
                    Streaming
                </Badge>
            )}
        </div>
        <h2 className={`mt-4 font-mono font-semibold text-zinc-100 ${mobile ? 'text-2xl leading-tight' : 'text-xl'}`}>
            {agent.name}
        </h2>
        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-500">
            <span>v{agent.version}</span>
            <span className="text-zinc-700">•</span>
            <span>{agent.author || agent.provider?.organization || 'Unknown'}</span>
            {agent.protocolVersion && (
                <>
                    <span className="text-zinc-700">•</span>
                    <span>A2A v{agent.protocolVersion}</span>
                </>
            )}
        </div>
        <p className={`mt-4 max-w-2xl text-zinc-300 ${mobile ? 'text-sm leading-7' : 'text-sm leading-relaxed'}`}>
            {agent.description}
        </p>
    </div>
);

const AgentSections = ({ agent, mobile, onOpenReport }) => {
    const websiteUrl = useMemo(() => (
        safeExternalUrl(agent.homepage) ||
        safeExternalUrl(agent.provider?.url) ||
        safeExternalUrl(agent.documentationUrl) ||
        safeExternalUrl(agent.url)
    ), [agent.documentationUrl, agent.homepage, agent.provider?.url, agent.url]);
    const documentationUrl = useMemo(() => safeExternalUrl(agent.documentationUrl), [agent.documentationUrl]);
    const sdkOrigin = useMemo(() => {
        const safeUrl = safeExternalUrl(agent.wellKnownURI) || safeExternalUrl(agent.url);
        if (!safeUrl) return agent.url;

        try {
            return new URL(safeUrl).origin;
        } catch {
            return agent.url;
        }
    }, [agent.url, agent.wellKnownURI]);

    return (
        <div className={`${mobile ? 'space-y-5 px-4 py-5' : 'space-y-8 p-6'}`}>
            <section className={`grid gap-3 ${mobile ? 'grid-cols-1' : 'grid-cols-2'}`}>
                <div className="border border-zinc-800 bg-zinc-950/60 p-4">
                    <p className="text-[10px] uppercase tracking-[0.28em] text-zinc-500">Trust & Health</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                        {agent.uptime_percentage !== null && agent.uptime_percentage !== undefined ? (
                            <HealthBadge
                                uptime={agent.uptime_percentage}
                                avgResponseTime={agent.avg_response_time_ms}
                                lastCheck={agent.last_health_check}
                                size="sm"
                            />
                        ) : (
                            <span className="text-sm text-zinc-500">No uptime data available.</span>
                        )}
                    </div>
                    {agent.status_notes?.length > 0 && (
                        <div className="mt-4 space-y-2">
                            {agent.status_notes.map((note, i) => {
                                const lower = note.toLowerCase();
                                const isCritical = lower.includes('unreachable') || lower.includes('low uptime');
                                return (
                                    <div
                                        key={i}
                                        className={`border px-3 py-2 text-[11px] ${
                                            isCritical
                                                ? 'border-red-800/50 bg-red-950/30 text-red-300'
                                                : 'border-amber-800/50 bg-amber-950/30 text-amber-300'
                                        }`}
                                    >
                                        {note}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                <div className="border border-zinc-800 bg-zinc-950/60 p-4">
                    <p className="text-[10px] uppercase tracking-[0.28em] text-zinc-500">Identity</p>
                    <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <dt className="text-[10px] uppercase tracking-[0.18em] text-zinc-600">Provider</dt>
                            <dd className="mt-1 text-zinc-200">{agent.author || agent.provider?.organization || 'Unknown'}</dd>
                        </div>
                        <div>
                            <dt className="text-[10px] uppercase tracking-[0.18em] text-zinc-600">License</dt>
                            <dd className="mt-1 text-zinc-200">{agent.license || 'MIT'}</dd>
                        </div>
                    </dl>
                    {agent.wellKnownURI && (
                        <div className="mt-4">
                            <CopyableField label="Agent Card URI" value={agent.wellKnownURI} />
                        </div>
                    )}
                </div>
            </section>

            <MaintainerNotes notes={agent.maintainer_notes} />

            <section className="border border-zinc-800 bg-black">
                <div className="border-b border-zinc-800 px-4 py-3">
                    <p className="text-[10px] uppercase tracking-[0.28em] text-zinc-500">Try the agent</p>
                    <h3 className="mt-1 text-lg font-semibold text-zinc-100">Live terminal</h3>
                </div>
                <div className={`${mobile ? 'h-[340px]' : 'h-64'}`}>
                    <Terminal agent={agent} autoFocusInput={!mobile} />
                </div>
            </section>

            <section className="border border-zinc-800 bg-zinc-950/60 p-4">
                <p className="text-[10px] uppercase tracking-[0.28em] text-zinc-500">Integration</p>
                <h3 className="mt-1 text-lg font-semibold text-zinc-100">Connect from code</h3>
                <Tabs defaultValue="registry" className="mt-4 w-full">
                    <TabsList className="grid h-auto w-full grid-cols-3 rounded-none border border-zinc-800 bg-zinc-900/50 p-0">
                        <TabsTrigger value="registry" className="h-11 rounded-none font-mono text-[10px] tracking-[0.18em] data-[state=active]:bg-zinc-800 data-[state=active]:text-emerald-400">
                            Registry
                        </TabsTrigger>
                        <TabsTrigger value="sdk" className="h-11 rounded-none font-mono text-[10px] tracking-[0.18em] data-[state=active]:bg-zinc-800 data-[state=active]:text-emerald-400">
                            SDK
                        </TabsTrigger>
                        <TabsTrigger value="curl" className="h-11 rounded-none font-mono text-[10px] tracking-[0.18em] data-[state=active]:bg-zinc-800 data-[state=active]:text-emerald-400">
                            CURL
                        </TabsTrigger>
                    </TabsList>
                    <TabsContent value="registry">
                        <pre className="overflow-x-auto border border-zinc-800 bg-black p-3 font-mono text-[10px] text-zinc-400">
{`import asyncio
from a2a_registry import AsyncRegistry

async def main():
    async with AsyncRegistry() as registry:
        agent = await registry.get_by_id("${agent.id}")
        client = await agent.async_connect()
        print(f"Connected to {agent.name}")

asyncio.run(main())`}
                        </pre>
                    </TabsContent>
                    <TabsContent value="sdk">
                        <pre className="overflow-x-auto border border-zinc-800 bg-black p-3 font-mono text-[10px] text-zinc-400">
{`import asyncio
from a2a.client import ClientFactory

async def main():
    client = await ClientFactory.connect(
        "${sdkOrigin}",
    )
    print("Connected via A2A SDK")

asyncio.run(main())`}
                        </pre>
                    </TabsContent>
                    <TabsContent value="curl">
                        <pre className="overflow-x-auto border border-zinc-800 bg-black p-3 font-mono text-[10px] text-zinc-400">
{`curl -X POST ${agent.url} \\
  -H "Content-Type: application/json" \\
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "messageId": "1",
        "role": "user",
        "parts": [{"kind": "text", "text": "Hello"}]
      }
    },
    "id": 1
  }'`}
                        </pre>
                    </TabsContent>
                </Tabs>
            </section>

            <section className={`grid gap-3 ${mobile ? 'grid-cols-1' : 'grid-cols-2'}`}>
                {websiteUrl ? (
                    <Button className="h-12 rounded-none bg-zinc-100 font-mono text-xs font-bold uppercase tracking-[0.18em] text-black hover:bg-white" asChild>
                        <a href={websiteUrl} target="_blank" rel="noopener noreferrer">
                            <Globe className="h-4 w-4" />
                            <span className="flex-1 text-center">Launch Website</span>
                            <ArrowUpRight className="h-4 w-4" />
                        </a>
                    </Button>
                ) : (
                    <Button disabled className="h-12 rounded-none bg-zinc-800 font-mono text-xs font-bold uppercase tracking-[0.18em] text-zinc-500">
                        <Globe className="h-4 w-4" />
                        <span className="flex-1 text-center">Launch Website unavailable</span>
                        <span className="h-4 w-4" aria-hidden="true" />
                    </Button>
                )}
                {documentationUrl ? (
                    <Button variant="outline" className="h-12 rounded-none border-zinc-700 bg-transparent font-mono text-xs uppercase tracking-[0.18em] text-zinc-300 hover:border-zinc-500 hover:text-zinc-100" asChild>
                        <a href={documentationUrl} target="_blank" rel="noopener noreferrer">
                            <FileText className="h-4 w-4" />
                            <span className="flex-1 text-center">Documentation</span>
                            <span className="h-4 w-4" aria-hidden="true" />
                        </a>
                    </Button>
                ) : (
                    <Button variant="outline" disabled className="h-12 rounded-none border-zinc-800 bg-transparent font-mono text-xs uppercase tracking-[0.18em] text-zinc-600">
                        <FileText className="h-4 w-4" />
                        <span className="flex-1 text-center">Documentation unavailable</span>
                        <span className="h-4 w-4" aria-hidden="true" />
                    </Button>
                )}
            </section>

            <Button
                variant="outline"
                onClick={onOpenReport}
                className="h-11 w-full rounded-none border-red-500/20 bg-red-950/20 font-mono text-xs uppercase tracking-[0.18em] text-red-300 hover:border-red-500/40 hover:bg-red-950/30"
            >
                <Flag className="mr-2 h-4 w-4" />
                Report this agent
            </Button>
        </div>
    );
};

const InspectionDeck = ({ agent, onClose, mobile = false }) => {
    const [showReport, setShowReport] = useState(false);

    if (!agent) {
        return (
            <aside className="flex h-full w-full flex-col items-center justify-center border-l border-zinc-800 bg-zinc-950 text-zinc-700">
                <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full border-2 border-zinc-800">
                    <Zap className="h-6 w-6" />
                </div>
                <p className="font-mono text-xs uppercase tracking-widest">No Agent Selected</p>
                <p className="mt-2 font-mono text-[10px]">Select an agent from the grid to inspect</p>
            </aside>
        );
    }

    if (mobile) {
        return (
            <>
                {showReport && <ReportModal agent={agent} onClose={() => setShowReport(false)} />}
                <section className="min-h-[calc(100vh-73px)] bg-black">
                    <div className="border-b border-zinc-800 bg-zinc-950/60 px-4 py-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-zinc-400 hover:text-zinc-200"
                        >
                            <ChevronLeft className="h-4 w-4" />
                            Back to results
                        </button>
                    </div>
                    <AgentHero agent={agent} mobile />
                    <AgentSections agent={agent} mobile onOpenReport={() => setShowReport(true)} />
                </section>
            </>
        );
    }

    return (
        <>
            {showReport && <ReportModal agent={agent} onClose={() => setShowReport(false)} />}
            <aside className="flex h-full w-full flex-col border-l border-zinc-800 bg-zinc-950">
                <div className="flex h-12 items-center justify-between border-b border-zinc-800 bg-zinc-900/30 px-4">
                    <div className="flex items-center gap-2">
                        <div className="h-2 w-2 animate-pulse bg-emerald-500" />
                        <span className="text-xs font-mono font-bold tracking-wider text-emerald-500">INSPECTION_DECK</span>
                    </div>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-zinc-500 hover:text-zinc-200" onClick={onClose}>
                        <X className="h-4 w-4" />
                    </Button>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar">
                    <AgentHero agent={agent} />
                    <AgentSections agent={agent} onOpenReport={() => setShowReport(true)} />
                </div>
            </aside>
        </>
    );
};

export default InspectionDeck;
