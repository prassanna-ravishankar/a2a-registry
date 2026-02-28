import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import Header from './Header';
import Sidebar from './Sidebar';
import InspectionDeck from './InspectionDeck';
import StatsBar from './StatsBar';
import { Button } from '@/components/ui/button';
import FeedbackWidget from './FeedbackWidget';

const Layout = ({
    children,
    searchTerm,
    setSearchTerm,
    agentCount,
    allTags,
    selectedSkills,
    toggleSkillFilter,
    conformanceFilter,
    setConformanceFilter,
    selectedAgent,
    onCloseInspection,
    stats
}) => {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    // Keyboard shortcut: "/" to focus search
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === '/' && !e.metaKey && !e.ctrlKey) {
                const searchInput = document.getElementById('global-agent-search');
                if (searchInput && document.activeElement !== searchInput) {
                    e.preventDefault();
                    searchInput.focus();
                }
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    return (
        <>
        <div className="flex flex-col h-screen bg-black text-zinc-200 overflow-hidden font-mono selection:bg-emerald-500/30 selection:text-emerald-200">
            <Header
                searchTerm={searchTerm}
                setSearchTerm={setSearchTerm}
                agentCount={agentCount}
                onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
            />

            <div className="flex flex-1 overflow-hidden relative">
                {/* Mobile Sidebar Overlay */}
                <div className={`absolute inset-0 z-40 !block md:!hidden transition-opacity duration-300 ${isMobileMenuOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}>
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setIsMobileMenuOpen(false)} />
                    <div className={`absolute inset-y-0 left-0 w-3/4 max-w-xs bg-zinc-950 border-r border-zinc-800 shadow-2xl transition-transform duration-300 ease-in-out flex flex-col ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}`}>
                        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
                            <span className="text-emerald-500 font-bold">SYSTEM_FILTERS</span>
                            <Button variant="ghost" size="icon" onClick={() => setIsMobileMenuOpen(false)}>
                                <X className="w-5 h-5" />
                            </Button>
                        </div>
                        <div className="flex-1 overflow-y-auto">
                            <Sidebar
                                allTags={allTags}
                                selectedSkills={selectedSkills}
                                toggleSkillFilter={toggleSkillFilter}
                                conformanceFilter={conformanceFilter}
                                setConformanceFilter={setConformanceFilter}
                                isMobile={true}
                            />
                        </div>
                    </div>
                </div>

                {/* Desktop Sidebar */}
                <div className="hidden md:flex w-64 shrink-0 h-full">
                    <Sidebar
                        allTags={allTags}
                        selectedSkills={selectedSkills}
                        toggleSkillFilter={toggleSkillFilter}
                        conformanceFilter={conformanceFilter}
                        setConformanceFilter={setConformanceFilter}
                    />
                </div>

                <main className="flex-1 flex flex-col relative min-w-0 md:border-r border-zinc-800">
                    {stats && <StatsBar stats={stats} />}
                    {children}
                </main>

                {selectedAgent && (
                    <div className="absolute inset-0 z-30 md:static md:z-auto md:w-[450px] md:shrink-0">
                        <InspectionDeck
                            agent={selectedAgent}
                            onClose={onCloseInspection}
                        />
                    </div>
                )}
            </div>
        </div>
        <FeedbackWidget />
        </>
    );
};

export default Layout;
