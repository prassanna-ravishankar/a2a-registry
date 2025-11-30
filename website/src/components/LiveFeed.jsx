import React, { useState, useEffect } from 'react';
import { Activity } from 'lucide-react';

const LiveFeed = () => {
    const [commits, setCommits] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchCommits = async () => {
            try {
                const response = await fetch(
                    'https://api.github.com/repos/prassanna-ravishankar/a2a-registry/commits?per_page=10'
                );
                const data = await response.json();
                setCommits(data);
                setLoading(false);
            } catch (error) {
                console.error('Failed to fetch commits:', error);
                setLoading(false);
            }
        };

        fetchCommits();
        // Refresh every 5 minutes
        const interval = setInterval(fetchCommits, 5 * 60 * 1000);
        return () => clearInterval(interval);
    }, []);

    const formatCommitMessage = (message) => {
        // Take first line only and truncate if needed
        const firstLine = message.split('\n')[0];
        return firstLine.length > 60 ? firstLine.substring(0, 57) + '...' : firstLine;
    };

    const formatTimestamp = (dateString) => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    return (
        <div className="border-t border-zinc-800 bg-black flex flex-col h-80">
            {/* Header */}
            <div className="flex items-center gap-2 px-4 py-2 border-b border-zinc-800 bg-zinc-900/30">
                <Activity className="w-3 h-3 text-emerald-500 animate-pulse" />
                <span className="text-[10px] font-mono font-bold text-emerald-500 tracking-widest uppercase">
                    Feed
                </span>
            </div>

            {/* Feed Content */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
                {loading ? (
                    <div className="text-zinc-600 text-[10px] font-mono">Loading activity...</div>
                ) : commits.length === 0 ? (
                    <div className="text-zinc-600 text-[10px] font-mono">No recent activity</div>
                ) : (
                    commits.map((commit) => (
                        <div
                            key={commit.sha}
                            className="text-[10px] font-mono group hover:bg-zinc-900/50 p-1 rounded transition-colors cursor-pointer"
                            onClick={() => window.open(commit.html_url, '_blank')}
                        >
                            <div className="flex items-start gap-2">
                                <span className="text-zinc-600 shrink-0">
                                    {formatTimestamp(commit.commit.author.date)}
                                </span>
                                <span className="text-amber-500 shrink-0">&gt;&gt;</span>
                                <span className="text-zinc-400 group-hover:text-zinc-200 transition-colors break-all">
                                    {formatCommitMessage(commit.commit.message)}
                                </span>
                            </div>
                            <div className="flex items-center gap-2 ml-[4.5rem] mt-0.5">
                                <span className="text-zinc-700 text-[9px]">
                                    {commit.sha.substring(0, 7)}
                                </span>
                                <span className="text-zinc-700 text-[9px]">
                                    {commit.commit.author.name}
                                </span>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Footer Metric */}
            <div className="border-t border-zinc-800 px-4 py-1.5 bg-zinc-900/50">
                <div className="flex items-center justify-between text-[9px] font-mono">
                    <span className="text-zinc-600">ACTIVITY_STATUS</span>
                    <span className="text-emerald-500">{commits.length > 0 ? 'ACTIVE' : 'IDLE'}</span>
                </div>
            </div>
        </div>
    );
};

export default LiveFeed;
