import React from 'react';
import { ExternalLink, BookOpen, Radio } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

const AgentCard = ({ agent, isSelected, onClick }) => {
    return (
        <div
            className={`
        relative group flex flex-col h-full transition-all duration-200 cursor-pointer
        border bg-zinc-950
        ${isSelected
                    ? 'border-emerald-500/50 bg-zinc-900/80 shadow-[0_0_20px_rgba(16,185,129,0.1)]'
                    : 'border-zinc-800 hover:border-zinc-700'
                }
      `}
            onClick={() => onClick(agent)}
        >
            {/* Corner Markers */}
            <div className={`absolute top-0 left-0 w-2 h-2 border-t border-l transition-colors ${isSelected ? 'border-emerald-500' : 'border-zinc-600'}`} />
            <div className={`absolute top-0 right-0 w-2 h-2 border-t border-r transition-colors ${isSelected ? 'border-emerald-500' : 'border-zinc-600'}`} />
            <div className={`absolute bottom-0 left-0 w-2 h-2 border-b border-l transition-colors ${isSelected ? 'border-emerald-500' : 'border-zinc-600'}`} />
            <div className={`absolute bottom-0 right-0 w-2 h-2 border-b border-r transition-colors ${isSelected ? 'border-emerald-500' : 'border-zinc-600'}`} />

            {/* Header */}
            <div className="p-4 border-b border-zinc-800/50">
                <div className="flex justify-between items-start mb-2">
                    <div className="min-w-0 flex-1 pr-4">
                        <h3 className={`font-mono font-bold text-sm truncate group-hover:text-emerald-400 transition-colors ${isSelected ? 'text-emerald-400' : 'text-zinc-200'}`}>
                            {agent.name}
                        </h3>
                        <div className="flex items-center gap-2 text-xs text-zinc-500 font-mono mt-1">
                            <span>v{agent.version}</span>
                            <span>•</span>
                            <span className="truncate">{agent.author || agent.provider?.organization || 'Unknown'}</span>
                        </div>
                    </div>

                    {/* Status Indicators */}
                    <div className="flex gap-1.5">
                        {agent.conformance === false && (
                            <TooltipProvider>
                                <Tooltip>
                                    <TooltipTrigger>
                                        <div className="w-2 h-2 rounded-full bg-amber-500/50 border border-amber-500/30" />
                                    </TooltipTrigger>
                                    <TooltipContent>Non-standard</TooltipContent>
                                </Tooltip>
                            </TooltipProvider>
                        )}
                        {agent.capabilities?.streaming && (
                            <TooltipProvider>
                                <Tooltip>
                                    <TooltipTrigger>
                                        <div className="w-2 h-2 rounded-full bg-emerald-500/50 border border-emerald-500/30 animate-pulse" />
                                    </TooltipTrigger>
                                    <TooltipContent>Streaming Enabled</TooltipContent>
                                </Tooltip>
                            </TooltipProvider>
                        )}
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 p-4 flex flex-col">
                <p className="text-xs text-zinc-400 font-mono leading-relaxed line-clamp-3 mb-4 flex-1">
                    {agent.description}
                </p>

                {/* Skills */}
                <div className="space-y-2">
                    {agent.skills.slice(0, 2).map((skill, idx) => (
                        <div key={idx} className="bg-zinc-900/50 border border-zinc-800/50 p-2">
                            <div className="text-[10px] text-emerald-500/80 font-mono uppercase tracking-wider mb-1">
                                {skill.name}
                            </div>
                            <div className="flex flex-wrap gap-1">
                                {(skill.tags || []).slice(0, 3).map((tag, tIdx) => (
                                    <span key={tIdx} className="text-[10px] text-zinc-500 bg-zinc-900 px-1 border border-zinc-800">
                                        {tag}
                                    </span>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Footer Actions */}
            <div className="p-3 border-t border-zinc-800 bg-zinc-900/30 flex gap-2">
                <Button
                    size="sm"
                    className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-black font-mono font-bold text-xs uppercase tracking-wider h-8 rounded-none"
                    asChild
                    onClick={(e) => e.stopPropagation()}
                >
                    <a href={agent.url} target="_blank" rel="noopener noreferrer">
                        Connect
                    </a>
                </Button>
                <Button
                    size="sm"
                    variant="outline"
                    className="flex-1 border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-zinc-100 font-mono text-xs uppercase tracking-wider h-8 rounded-none bg-transparent"
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
