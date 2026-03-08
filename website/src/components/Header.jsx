import React from 'react';
import { Search, Menu, Plus, ArrowLeft, SlidersHorizontal } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

const Header = ({
    searchTerm,
    setSearchTerm,
    agentCount,
    total,
    isMobile,
    selectedAgent,
    onOpenMobileMenu,
    onBack,
    activeFilterCount,
}) => {
    if (isMobile && selectedAgent) {
        return (
            <header className="sticky top-0 z-50 border-b border-zinc-800/80 bg-black/95 backdrop-blur">
                <div className="flex items-center gap-3 px-4 py-3">
                    <Button
                        variant="ghost"
                        size="icon"
                        className="-ml-2 h-10 w-10 text-zinc-400"
                        onClick={onBack}
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </Button>
                    <div className="min-w-0 flex-1">
                        <p className="text-[10px] uppercase tracking-[0.28em] text-emerald-500/80">Agent Detail</p>
                        <h1 className="truncate font-mono text-sm font-semibold text-zinc-100">{selectedAgent.name}</h1>
                    </div>
                    <a
                        href="/submit"
                        className="inline-flex h-10 items-center gap-1.5 border border-emerald-500/40 bg-emerald-500/10 px-3 text-[10px] font-mono uppercase tracking-[0.2em] text-emerald-300"
                    >
                        <Plus className="w-3 h-3" />
                        Submit
                    </a>
                </div>
            </header>
        );
    }

    if (isMobile) {
        return (
            <header className="sticky top-0 z-50 border-b border-zinc-800/80 bg-black/95 backdrop-blur">
                <div className="flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-3 min-w-0">
                        <Button variant="ghost" size="icon" className="-ml-2 h-10 w-10 text-zinc-400" onClick={onOpenMobileMenu}>
                            <Menu className="w-5 h-5" />
                        </Button>
                        <div className="flex items-center gap-3 min-w-0">
                            <div className="flex h-9 w-9 items-center justify-center border border-zinc-800 bg-zinc-900">
                                <img src="/logo.png" alt="A2A Registry" className="w-5 h-5" />
                            </div>
                            <div className="min-w-0">
                                <h1 className="truncate font-mono text-sm font-bold tracking-[0.18em] text-zinc-100">
                                    A2A_REGISTRY
                                </h1>
                                <p className="text-[10px] uppercase tracking-[0.24em] text-zinc-500">
                                    {total ? `${agentCount} of ${total} visible` : `${agentCount} visible`}
                                </p>
                            </div>
                        </div>
                    </div>

                    <a
                        href="/submit"
                        className="inline-flex h-10 items-center gap-1.5 border border-emerald-500/40 bg-emerald-500/10 px-3 text-[10px] font-mono uppercase tracking-[0.18em] text-emerald-300"
                    >
                        <Plus className="w-3 h-3" />
                        Submit
                    </a>
                </div>

                <div className="space-y-3 px-4 pb-4">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" />
                        <Input
                            id="global-agent-search"
                            className="h-11 border-zinc-800 bg-zinc-950 pl-10 font-mono text-sm text-zinc-100 placeholder:text-zinc-600 focus:border-emerald-500/60 focus:ring-0"
                            placeholder="Search agents, skills, authors"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>

                    <div className="flex items-center gap-2 overflow-x-auto pb-1">
                        <button
                            type="button"
                            onClick={onOpenMobileMenu}
                            className="inline-flex h-9 shrink-0 items-center gap-2 border border-zinc-800 bg-zinc-950 px-3 text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-300"
                        >
                            <SlidersHorizontal className="h-3.5 w-3.5 text-emerald-400" />
                            Filters
                            {activeFilterCount > 0 && (
                                <span className="inline-flex min-w-5 items-center justify-center border border-emerald-500/40 bg-emerald-500/10 px-1 text-[10px] text-emerald-300">
                                    {activeFilterCount}
                                </span>
                            )}
                        </button>
                        <div className="inline-flex h-9 shrink-0 items-center gap-2 border border-zinc-800 bg-zinc-950 px-3 text-[11px] font-mono uppercase tracking-[0.18em] text-zinc-400">
                            <span className="h-2 w-2 rounded-full bg-emerald-500" />
                            Registry Live
                        </div>
                    </div>
                </div>
            </header>
        );
    }

    return (
        <header className="h-12 border-b border-zinc-800 bg-zinc-950 flex items-center px-4 justify-between shrink-0 sticky top-0 z-50">
            <div className="flex items-center gap-4">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-zinc-900 border border-zinc-800 flex items-center justify-center">
                        <img src="/logo.png" alt="A2A Registry" className="w-5 h-5" />
                    </div>
                    <h1 className="font-mono font-bold text-zinc-100 tracking-wider text-sm">
                        A2A_REGISTRY <span className="hidden md:inline text-zinc-600 text-xs font-normal">// V2_INTERFACE</span>
                    </h1>
                </div>

                <div className="hidden md:flex items-center gap-4 text-[10px] font-mono text-zinc-500 border-l border-zinc-800 pl-4">
                    <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                        <span className="text-emerald-500">REGISTRY_ONLINE</span>
                    </div>
                    <span>v2.0.0</span>
                </div>
            </div>

            <div className="flex-1 max-w-md mx-2 md:mx-4">
                <div className="relative group">
                    <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-zinc-500 group-focus-within:text-emerald-500 transition-colors" />
                    <Input
                        id="global-agent-search"
                        className="h-8 bg-zinc-900 border-zinc-800 text-zinc-200 text-xs font-mono pl-8 focus:border-emerald-500/50 focus:ring-0 placeholder:text-zinc-600"
                        placeholder="SEARCH..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            <div className="flex items-center gap-4 text-xs font-mono">
                <div className="hidden md:block text-zinc-500">
                    AGENTS_ACTIVE: <span className="text-zinc-200">{total || agentCount}</span>
                </div>
                <a
                    href="/submit"
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/20 hover:border-emerald-500 transition-all text-[10px] md:text-xs font-mono uppercase tracking-wider"
                >
                    <Plus className="w-3 h-3" />
                    <span className="hidden md:inline">SUBMIT_AGENT</span>
                    <span className="md:hidden">SUBMIT</span>
                </a>
            </div>
        </header>
    );
};

export default Header;
