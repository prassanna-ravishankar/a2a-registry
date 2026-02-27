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
    return (
        <aside className={`${isMobile ? 'w-full border-none' : 'w-64 border-r'} border-zinc-800 bg-zinc-950 flex flex-col h-full shrink-0`}>
            {/* Section Header */}
            <div className="h-10 border-b border-zinc-800 flex items-center px-4 bg-zinc-900/30">
                <Filter className="w-3 h-3 text-emerald-500 mr-2" />
                <span className="text-xs font-mono font-bold text-zinc-400 tracking-wider">FILTERS & TELEMETRY</span>
            </div>

            <div className="flex-1 overflow-y-auto custom-scrollbar">
                <div className="p-4 space-y-6">
                    {/* Conformance Filter */}
                    <div className="space-y-3">
                        <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Protocol Conformance</div>
                        <div className="space-y-1">
                            {[
                                { id: 'standard', label: 'STANDARD_ONLY', color: 'text-emerald-500' },
                                { id: 'non-standard', label: 'NON_STANDARD', color: 'text-amber-500' },
                                { id: 'all', label: 'SHOW_ALL', color: 'text-zinc-400' }
                            ].map((option) => (
                                <button
                                    key={option.id}
                                    onClick={() => setConformanceFilter(option.id)}
                                    className={`
                                        w-full text-left px-2 py-1.5 text-xs font-mono border transition-all
                                        ${conformanceFilter === option.id
                                            ? 'bg-zinc-900 border-emerald-500/50 text-zinc-200'
                                            : 'border-transparent hover:bg-zinc-900/50 text-zinc-500'
                                        }
                                    `}
                                >
                                    <div className="flex items-center justify-between">
                                        <span>{option.label}</span>
                                        {conformanceFilter === option.id && (
                                            <div className={`w-1.5 h-1.5 rounded-full ${option.id === 'non-standard' ? 'bg-amber-500' : 'bg-emerald-500'} `} />
                                        )}
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Skill Cloud */}
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <div className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest">Skill Modules</div>
                            {selectedSkills.length > 0 && (
                                <button
                                    onClick={() => selectedSkills.forEach(t => toggleSkillFilter(t))}
                                    className="text-[10px] font-mono text-zinc-500 hover:text-zinc-300 flex items-center gap-1"
                                >
                                    <X className="w-2.5 h-2.5" /> clear
                                </button>
                            )}
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                            {allTags.slice(0, 20).map(tag => {
                                const active = selectedSkills.includes(tag);
                                return (
                                    <Badge
                                        key={tag}
                                        variant="outline"
                                        className={`
                                            cursor-pointer text-[10px] font-mono rounded-none border transition-all flex items-center gap-1
                                            ${active
                                                ? 'bg-emerald-900/20 border-emerald-500/50 text-emerald-400'
                                                : 'bg-zinc-900/50 border-zinc-800 text-zinc-500 hover:border-zinc-600'
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

            {/* Live Feed - Desktop Only */}
            {!isMobile && <LiveFeed />}
        </aside>
    );
};

export default Sidebar;
