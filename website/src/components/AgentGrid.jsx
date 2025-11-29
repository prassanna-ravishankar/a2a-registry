import React from 'react';
import { Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import AgentCard from './AgentCard';

const AgentGrid = ({
    agents,
    loading,
    error,
    selectedAgent,
    onAgentSelect,
    onClearFilters
}) => {
    if (loading) {
        return (
            <div className="flex-1 p-6">
                {/* Grid */}
                <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
                        <div key={i} className="h-64 bg-zinc-900/50 border border-zinc-800 animate-pulse" />
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
        <div className="flex-1 bg-black overflow-y-auto custom-scrollbar relative">
            {/* Grid Background Effect */}
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#18181b_1px,transparent_1px),linear-gradient(to_bottom,#18181b_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none" />

            <div className="relative p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {agents.map((agent, index) => (
                    <AgentCard
                        key={index}
                        agent={agent}
                        isSelected={selectedAgent?.name === agent.name}
                        onClick={onAgentSelect}
                    />
                ))}
            </div>
        </div>
    );
};

export default AgentGrid;
