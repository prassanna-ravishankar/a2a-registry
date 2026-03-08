import React from 'react';
import { Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import AgentCard from './AgentCard';

const AgentGrid = ({
    agents,
    loading,
    error,
    loadingMore,
    total,
    selectedAgent,
    onAgentSelect,
    onLoadMore,
    onClearFilters
}) => {
    if (loading) {
        return (
            <div className="flex-1 p-4 md:p-6">
                <div className="grid grid-cols-1 gap-4 p-0 md:grid-cols-2 lg:grid-cols-3 md:p-4">
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                        <div key={i} className="h-64 border border-zinc-800 bg-zinc-900/50 animate-pulse" />
                    ))}
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-500">
                <div className="text-4xl mb-4">⚠️</div>
                <h2 className="text-xl font-mono font-bold text-zinc-300 mb-2">SYSTEM_ERROR</h2>
                <p className="font-mono text-sm">{error}</p>
            </div>
        );
    }

    if (agents.length === 0) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-500">
                <div className="w-24 h-24 border-2 border-zinc-800 rounded-full flex items-center justify-center mb-6">
                    <Search className="w-10 h-10 text-zinc-700" />
                </div>
                <h2 className="text-xl font-mono font-bold text-zinc-300 mb-2">NO_AGENTS_FOUND</h2>
                <p className="font-mono text-sm mb-6">Adjust search parameters or filters</p>
                <Button
                    variant="outline"
                    onClick={onClearFilters}
                    className="border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-zinc-100 font-mono text-xs uppercase tracking-wider rounded-none bg-transparent"
                >
                    Reset Filters
                </Button>
            </div>
        );
    }

    return (
        <div className="relative flex-1 overflow-x-hidden bg-black">
            <div className="pointer-events-none absolute inset-0 hidden bg-[linear-gradient(to_right,#18181b_1px,transparent_1px),linear-gradient(to_bottom,#18181b_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] md:block" />

            <div className="relative mx-auto w-full max-w-7xl px-4 pb-10 pt-5 md:px-6 md:pt-6">
                <div className="mb-5 flex flex-col gap-3 border border-zinc-800 bg-zinc-950/60 p-4 md:hidden">
                    <div className="flex items-baseline justify-between gap-3">
                        <div>
                            <p className="text-[10px] uppercase tracking-[0.28em] text-zinc-500">Browse agents</p>
                            <h2 className="mt-1 text-xl font-semibold text-zinc-100">{agents.length} results</h2>
                        </div>
                        {typeof total === 'number' && total > agents.length && (
                            <Badge variant="outline" className="rounded-none border-zinc-700 bg-zinc-900 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-400">
                                {total} total
                            </Badge>
                        )}
                    </div>
                    <p className="text-sm leading-6 text-zinc-400">
                        Scan by trust signals first, then open a full detail view for deeper inspection.
                    </p>
                </div>

                <div className="grid w-full grid-cols-1 gap-4 md:grid-cols-2 md:gap-6 lg:grid-cols-3 xl:grid-cols-4">
                {agents.map((agent, index) => (
                    <AgentCard
                        key={index}
                        agent={agent}
                        isSelected={selectedAgent?.name === agent.name}
                        onClick={onAgentSelect}
                    />
                ))}
                </div>

                {onLoadMore && (
                    <div className="mt-8 flex justify-center">
                        <Button
                            variant="outline"
                            onClick={onLoadMore}
                            disabled={loadingMore}
                            className="rounded-none border-zinc-700 bg-zinc-950 px-6 py-3 font-mono text-xs uppercase tracking-[0.22em] text-zinc-200 hover:border-emerald-500/40 hover:text-emerald-300"
                        >
                            {loadingMore ? 'Loading...' : 'Load More Agents'}
                        </Button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AgentGrid;
