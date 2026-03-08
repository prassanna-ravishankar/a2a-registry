import React from 'react';
import { Filter, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import LiveFeed from './LiveFeed';

const Sidebar = ({
    allTags,
    selectedSkills,
    toggleSkillFilter,
    conformanceFilter,
    setConformanceFilter,
    isMobile
}) => {
    const filterOptions = [
        { id: 'standard', label: 'STANDARD_ONLY', description: 'A2A-conformant agents', color: 'text-emerald-500' },
        { id: 'non-standard', label: 'NON_STANDARD', description: 'Looser protocol support', color: 'text-amber-500' },
        { id: 'all', label: 'SHOW_ALL', description: 'Browse the full registry', color: 'text-zinc-400' }
    ];

    return (
        <aside className={`${isMobile ? 'w-full border-none' : 'w-64 border-r'} border-zinc-800 bg-zinc-950 flex flex-col h-full shrink-0`}>
            <div className="flex items-center gap-2 border-b border-zinc-800 bg-zinc-900/30 px-4 py-3">
                <Filter className="w-3 h-3 text-emerald-500" />
                <span className="text-xs font-mono font-bold text-zinc-400 tracking-wider">
                    {isMobile ? 'FILTERS' : 'FILTERS & TELEMETRY'}
                </span>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar">
                <div className="space-y-6 p-4">
                    <div className="rounded-sm border border-zinc-800 bg-black/40 p-4">
                        <p className="text-[10px] uppercase tracking-[0.28em] text-zinc-500">Current filters</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                            <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 font-mono text-[10px] uppercase tracking-[0.18em] text-emerald-300">
                                {filterOptions.find((option) => option.id === conformanceFilter)?.label}
                            </Badge>
                            {selectedSkills.map((tag) => (
                                <Badge
                                    key={tag}
                                    variant="outline"
                                    className="cursor-pointer border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[10px] text-zinc-300"
                                    onClick={() => toggleSkillFilter(tag)}
                                >
                                    {tag}
                                    <X className="ml-1 h-2.5 w-2.5" />
                                </Badge>
                            ))}
                            {selectedSkills.length === 0 && (
                                <span className="text-xs text-zinc-500">No skill filters selected</span>
                            )}
                        </div>
                    </div>

                    <div className="space-y-3">
                        <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Protocol Conformance</div>
                        <div className="space-y-2">
                            {filterOptions.map((option) => (
                                <button
                                    key={option.id}
                                    onClick={() => setConformanceFilter(option.id)}
                                    className={`
                                        w-full border px-3 py-3 text-left transition-all
                                        ${conformanceFilter === option.id
                                            ? 'border-emerald-500/50 bg-emerald-500/10'
                                            : 'border-zinc-800 bg-zinc-900/40 hover:border-zinc-700'
                                        }
                                    `}
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div>
                                            <div className={`text-xs font-mono ${conformanceFilter === option.id ? 'text-zinc-100' : 'text-zinc-300'}`}>{option.label}</div>
                                            <div className="mt-1 text-[11px] text-zinc-500">{option.description}</div>
                                        </div>
                                        <div className={`mt-1 h-2 w-2 rounded-full ${conformanceFilter === option.id ? (option.id === 'non-standard' ? 'bg-amber-500' : 'bg-emerald-500') : 'bg-zinc-700'}`} />
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Skill Modules</div>
                            {selectedSkills.length > 0 && (
                                <button
                                    onClick={() => selectedSkills.forEach(t => toggleSkillFilter(t))}
                                    className="text-[10px] font-mono text-zinc-500 hover:text-zinc-300 flex items-center gap-1 uppercase tracking-[0.18em]"
                                >
                                    <X className="w-2.5 h-2.5" /> clear
                                </button>
                            )}
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {allTags.slice(0, 20).map(tag => {
                                const active = selectedSkills.includes(tag);
                                return (
                                    <Badge
                                        key={tag}
                                        variant="outline"
                                        className={`
                                            cursor-pointer text-[10px] font-mono rounded-none border transition-all flex items-center gap-1 px-2.5 py-1.5
                                            ${active
                                                ? 'bg-emerald-900/20 border-emerald-500/50 text-emerald-400'
                                                : 'bg-zinc-900/50 border-zinc-800 text-zinc-400 hover:border-zinc-600'
                                            }
                                        `}
                                        onClick={() => toggleSkillFilter(tag)}
                                    >
                                        {tag}
                                        {active && <X className="w-2.5 h-2.5 ml-0.5" />}
                                    </Badge>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>

            <div className="px-3 pb-3 border-t border-zinc-800 pt-3">
                <div className="text-[10px] font-mono text-zinc-600 uppercase tracking-widest mb-2">MCP Access</div>
                <p className="text-[10px] text-zinc-600 mb-2 leading-relaxed">
                    Use this registry from Claude, Cursor, or any MCP client:
                </p>
                <pre className="text-[9px] text-emerald-400/70 bg-zinc-900 border border-zinc-800 p-2 overflow-x-auto leading-relaxed">{`"a2a-registry": {
  "url": "https://a2aregistry.org/mcp/"
}`}</pre>
            </div>

            {/* Live Feed - Desktop Only */}
            {!isMobile && <LiveFeed />}
        </aside>
    );
};

export default Sidebar;
