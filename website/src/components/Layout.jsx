import React from 'react';
import Header from './Header';
import Sidebar from './Sidebar';
import InspectionDeck from './InspectionDeck';

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
    onCloseInspection
}) => {
    return (
        <div className="flex flex-col h-screen bg-black text-zinc-200 overflow-hidden font-mono selection:bg-emerald-500/30 selection:text-emerald-200">
            <Header
                searchTerm={searchTerm}
                setSearchTerm={setSearchTerm}
                agentCount={agentCount}
            />

            <div className="flex flex-1 overflow-hidden">
                <Sidebar
                    allTags={allTags}
                    selectedSkills={selectedSkills}
                    toggleSkillFilter={toggleSkillFilter}
                    conformanceFilter={conformanceFilter}
                    setConformanceFilter={setConformanceFilter}
                />

                <main className="flex-1 flex flex-col relative min-w-0 border-r border-zinc-800">
                    {children}
                </main>

                {selectedAgent && (
                    <InspectionDeck
                        agent={selectedAgent}
                        onClose={onCloseInspection}
                    />
                )}
            </div>
        </div>
    );
};

export default Layout;
