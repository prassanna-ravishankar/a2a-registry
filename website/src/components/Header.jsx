import React from 'react';
import { Search, Activity, Menu } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

const Header = ({ searchTerm, setSearchTerm, agentCount, onOpenMobileMenu }) => {
    return (
        <header className="h-12 border-b border-zinc-800 bg-zinc-950 flex items-center px-4 justify-between shrink-0 z-50">
            {/* Left: Brand & Status */}
            <div className="flex items-center gap-4">
                <Button variant="ghost" size="icon" className="md:hidden -ml-2 text-zinc-400" onClick={onOpenMobileMenu}>
                    <Menu className="w-5 h-5" />
                </Button>
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-zinc-900 border border-zinc-800 flex items-center justify-center">
                        <img src="/logo.png" alt="A2A Registry" className="w-5 h-5" />
                    </div>
                    <h1 className="font-mono font-bold text-zinc-100 tracking-wider text-sm">
                        A2A_REGISTRY <span className="text-zinc-600 text-xs font-normal">// V2_INTERFACE</span>
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

            {/* Center: Search */}
            <div className="flex-1 max-w-md mx-4">
                <div className="relative group">
                    <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-zinc-500 group-focus-within:text-emerald-500 transition-colors" />
                    <Input
                        className="h-8 bg-zinc-900 border-zinc-800 text-zinc-200 text-xs font-mono pl-8 focus:border-emerald-500/50 focus:ring-0 placeholder:text-zinc-600"
                        placeholder="SEARCH_AGENTS..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>
            </div>

            {/* Right: Metrics */}
            <div className="flex items-center gap-4 text-xs font-mono">
                <div className="text-zinc-500">
                    AGENTS_ACTIVE: <span className="text-zinc-200">{agentCount}</span>
                </div>
            </div>
        </header>
    );
};

export default Header;
