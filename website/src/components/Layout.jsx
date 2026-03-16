import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import Header from './Header';
import Sidebar from './Sidebar';
import InspectionDeck from './InspectionDeck';
import StatsBar from './StatsBar';
import { Button } from '@/components/ui/button';
import FeedbackWidget from './FeedbackWidget';
import { Dialog, DialogContent } from '@/components/ui/dialog';

const Layout = ({
    isMobile,
    children,
    searchTerm,
    setSearchTerm,
    agentCount,
    total,
    allTags,
    selectedSkills,
    toggleSkillFilter,
    conformanceFilter,
    setConformanceFilter,
    healthyOnly,
    setHealthyOnly,
    selectedAgent,
    onCloseInspection,
    stats
}) => {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const activeFilterCount = selectedSkills.length + (conformanceFilter !== 'standard' ? 1 : 0);

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
        <div className="min-h-screen bg-black text-zinc-200 font-mono selection:bg-emerald-500/30 selection:text-emerald-200">
            <Header
                isMobile={isMobile}
                searchTerm={searchTerm}
                setSearchTerm={setSearchTerm}
                agentCount={agentCount}
                total={total}
                activeFilterCount={activeFilterCount}
                selectedAgent={selectedAgent}
                onBack={onCloseInspection}
                onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
            />

            <div className="relative md:flex">
                <div className="hidden md:flex md:w-64 md:shrink-0 md:sticky md:top-0 md:h-screen md:overflow-y-auto">
                    <Sidebar
                        allTags={allTags}
                        selectedSkills={selectedSkills}
                        toggleSkillFilter={toggleSkillFilter}
                        conformanceFilter={conformanceFilter}
                        setConformanceFilter={setConformanceFilter}
                        healthyOnly={healthyOnly}
                        setHealthyOnly={setHealthyOnly}
                    />
                </div>

                {isMobile ? (
                    selectedAgent ? (
                        <main className="min-w-0 flex-1">
                            <InspectionDeck
                                agent={selectedAgent}
                                onClose={onCloseInspection}
                                mobile
                            />
                        </main>
                    ) : (
                        <main className="min-w-0 flex-1">
                            {stats && <StatsBar stats={stats} />}
                            {children}
                        </main>
                    )
                ) : (
                    <>
                        <main className="flex min-w-0 flex-1 flex-col">
                            {stats && <StatsBar stats={stats} />}
                            {children}
                        </main>

                        <Dialog open={Boolean(selectedAgent)} onOpenChange={(open) => !open && onCloseInspection()}>
                            <DialogContent className="left-1/2 top-1/2 flex h-[min(88vh,900px)] w-[min(1100px,calc(100vw-64px))] max-w-none -translate-x-1/2 -translate-y-1/2 overflow-hidden border-zinc-800 bg-zinc-950 p-0 text-zinc-200 sm:rounded-none">
                                {selectedAgent && (
                                    <InspectionDeck
                                        agent={selectedAgent}
                                        onClose={onCloseInspection}
                                    />
                                )}
                            </DialogContent>
                        </Dialog>
                    </>
                )}
            </div>
        </div>
        {isMobile && isMobileMenuOpen && (
            <div className="fixed inset-0 z-50 flex items-end bg-black/75 backdrop-blur-sm" onClick={() => setIsMobileMenuOpen(false)}>
                <div
                    className="max-h-[88vh] w-full overflow-hidden border-t border-zinc-800 bg-zinc-950 shadow-2xl"
                    onClick={(e) => e.stopPropagation()}
                >
                    <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-4">
                        <div>
                            <p className="text-[10px] uppercase tracking-[0.28em] text-zinc-500">Browse Controls</p>
                            <h2 className="text-lg font-semibold text-emerald-400">Filters</h2>
                        </div>
                        <Button variant="ghost" size="icon" className="text-zinc-500" onClick={() => setIsMobileMenuOpen(false)}>
                            <X className="w-5 h-5" />
                        </Button>
                    </div>
                    <div className="max-h-[calc(88vh-73px)] overflow-y-auto overscroll-contain">
                        <Sidebar
                            allTags={allTags}
                            selectedSkills={selectedSkills}
                            toggleSkillFilter={toggleSkillFilter}
                            conformanceFilter={conformanceFilter}
                            setConformanceFilter={setConformanceFilter}
                            isMobile
                        />
                    </div>
                </div>
            </div>
        )}
        <FeedbackWidget />
        </>
    );
};

export default Layout;
