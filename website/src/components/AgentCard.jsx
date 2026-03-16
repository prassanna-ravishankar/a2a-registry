import React from 'react';
import { ArrowUpRight, ShieldCheck, ShieldAlert, Radio, CheckCircle2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import HealthBadge from './HealthBadge';

const AgentCard = ({ agent, isSelected, onClick }) => {
    const provider = agent.author || agent.provider?.organization || 'Unknown';
    const topTags = agent.skills.flatMap((skill) => skill.tags || []).slice(0, 3);
    const notes = agent.maintainer_notes || '';
    const isVerified = notes.startsWith('Verified working');
    const hasIssue = notes && !isVerified;

    return (
        <div
            className={`
        group flex h-full cursor-pointer flex-col border bg-zinc-950/90 transition-all duration-200
        ${isSelected
                    ? 'border-emerald-500/50 bg-zinc-900/80 shadow-[0_0_20px_rgba(16,185,129,0.1)]'
                    : 'border-zinc-800 hover:border-zinc-700 hover:bg-zinc-950'
                }
      `}
            onClick={() => onClick(agent)}
        >
            <div className="flex items-start justify-between gap-3 border-b border-zinc-800/60 p-4 md:p-5">
                <div className="min-w-0 flex-1">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                        <Badge
                            variant="outline"
                            className={`rounded-none border px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] ${
                                agent.conformance === false
                                    ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                                    : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                            }`}
                        >
                            {agent.conformance === false ? (
                                <>
                                    <ShieldAlert className="mr-1 h-3 w-3" />
                                    Non-standard
                                </>
                            ) : (
                                <>
                                    <ShieldCheck className="mr-1 h-3 w-3" />
                                    Conformant
                                </>
                            )}
                        </Badge>
                        {agent.capabilities?.streaming && (
                            <Badge variant="outline" className="rounded-none border-cyan-500/30 bg-cyan-500/10 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-cyan-300">
                                <Radio className="mr-1 h-3 w-3" />
                                Streaming
                            </Badge>
                        )}
                        {isVerified && (
                            <Badge variant="outline" className="rounded-none border-blue-500/30 bg-blue-500/10 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-blue-300">
                                <CheckCircle2 className="mr-1 h-3 w-3" />
                                Verified
                            </Badge>
                        )}
                    </div>
                    <h3 className={`font-mono text-base font-semibold leading-tight transition-colors group-hover:text-emerald-300 ${isSelected ? 'text-emerald-300' : 'text-zinc-100'}`}>
                        {agent.name}
                    </h3>
                    <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-500">
                        <span>v{agent.version}</span>
                        <span className="text-zinc-700">•</span>
                        <span className="truncate">{provider}</span>
                    </div>
                </div>
                <ArrowUpRight className="mt-1 h-4 w-4 shrink-0 text-zinc-600 transition-colors group-hover:text-emerald-400" />
            </div>

            <div className="flex flex-1 flex-col gap-4 p-4 md:p-5">
                <p className="text-sm leading-6 text-zinc-300 line-clamp-3 md:text-xs md:leading-relaxed">
                    {agent.description}
                </p>

                <div className="flex flex-wrap gap-2">
                    {agent.uptime_percentage !== null && agent.uptime_percentage !== undefined && (
                        <HealthBadge
                            uptime={agent.uptime_percentage}
                            avgResponseTime={agent.avg_response_time_ms}
                            lastCheck={agent.last_health_check}
                            size="sm"
                        />
                    )}
                    {agent.protocolVersion && (
                        <Badge variant="outline" className="rounded-none border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-300">
                            A2A v{agent.protocolVersion}
                        </Badge>
                    )}
                    {hasIssue && (
                        <Badge variant="outline" className="rounded-none border-amber-700/30 bg-amber-900/20 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-amber-400" title={notes}>
                            <AlertTriangle className="mr-1 h-3 w-3" />
                            Issue noted
                        </Badge>
                    )}
                </div>

                <div className="flex flex-wrap gap-2">
                    {topTags.map((tag) => (
                        <span
                            key={tag}
                            className="border border-zinc-800 bg-zinc-900 px-2 py-1 text-[11px] text-zinc-400"
                        >
                            {tag}
                        </span>
                    ))}
                </div>
            </div>

            <div className="border-t border-zinc-800 bg-zinc-900/30 p-3">
                <Button
                    className="h-11 w-full rounded-none bg-emerald-600 font-mono text-xs font-bold uppercase tracking-[0.22em] text-black hover:bg-emerald-500"
                    onClick={(e) => {
                        e.stopPropagation();
                        onClick(agent);
                    }}
                >
                    Inspect
                </Button>
            </div>
        </div>
    );
};

export default AgentCard;
