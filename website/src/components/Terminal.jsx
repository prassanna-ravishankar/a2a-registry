import React, { useState, useEffect, useRef } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const Terminal = ({ agent }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [ready, setReady] = useState(false);
    const [error, setError] = useState(null);
    const [contextId, setContextId] = useState(null);
    const bottomRef = useRef(null);

    const [systemLogs, setSystemLogs] = useState([]);

    useEffect(() => {
        const now = new Date();
        setMessages([]);
        setError(null);
        setReady(false);
        const newContextId = crypto.randomUUID();
        setContextId(newContextId);
        setSystemLogs([
            { type: 'system', content: `INITIALIZING CONNECTION TO ${agent.name.toUpperCase()}...`, timestamp: now },
            { type: 'system', content: `PROTOCOL: A2A v${agent.protocolVersion || agent.version || '0.3'}`, timestamp: now },
            { type: 'success', content: 'PROXY READY. TYPE YOUR MESSAGE OR ASK A QUESTION.', timestamp: now },
        ]);
        setReady(true);
    }, [agent]);

    // Auto-scroll
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, systemLogs]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim() || !ready || isLoading) return;

        const userMessage = input;
        setInput('');
        setIsLoading(true);
        setMessages(prev => [...prev, { type: 'request', content: userMessage, timestamp: new Date() }]);

        try {
            const res = await fetch(`${API_BASE}/agents/${agent.id}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: userMessage, context_id: contextId }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }

            const data = await res.json();
            setMessages(prev => [...prev, { type: 'response', content: data.response, timestamp: new Date() }]);
        } catch (err) {
            console.error('Chat proxy error:', err);
            setMessages(prev => [
                ...prev,
                { type: 'error', content: `ERROR: ${err.message}`, timestamp: new Date() },
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    const getLogStyle = (type) => {
        switch (type) {
            case 'request': return 'text-cyan-400';
            case 'response': return 'text-emerald-400';
            case 'system': return 'text-amber-500';
            case 'success': return 'text-emerald-500';
            case 'error': return 'text-red-500';
            case 'info': return 'text-zinc-400';
            default: return 'text-zinc-400';
        }
    };

    const getPrefix = (type) => {
        switch (type) {
            case 'request': return '>>';
            case 'response': return '<<';
            case 'system': return '!!';
            case 'error': return 'XX';
            case 'info': return '--';
            default: return '--';
        }
    };

    // Combine system logs with chat messages
    const displayLogs = [
        ...systemLogs,
        ...messages
    ];

    return (
        <div className="flex flex-col h-full bg-black border border-zinc-800 font-mono text-xs">
            {/* Terminal Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800 bg-zinc-900/50">
                <span className="text-zinc-400">TERMINAL_OUTPUT</span>
                <div className="flex gap-1.5">
                    <div className={`w-2 h-2 rounded-full ${error ? 'bg-red-500' : ready ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                    <div className="w-2 h-2 rounded-full bg-zinc-700" />
                    <div className="w-2 h-2 rounded-full bg-zinc-700" />
                </div>
            </div>

            {/* Logs Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-1 font-mono">
                {displayLogs.map((log, i) => (
                    <div key={i} className="flex gap-2">
                        <span className="text-zinc-600 shrink-0">[{log.timestamp?.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) || '--:--:--'}]</span>
                        <span className={`font-bold shrink-0 w-6 ${getLogStyle(log.type)}`}>{getPrefix(log.type)}</span>
                        <span className={`${getLogStyle(log.type)} break-all whitespace-pre-wrap`}>{log.content}</span>
                    </div>
                ))}
                {isLoading && (
                    <div className="flex gap-2">
                        <span className="text-zinc-600 shrink-0">[{new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span>
                        <span className="font-bold shrink-0 w-6 text-zinc-500">--</span>
                        <span className="text-zinc-500 animate-pulse">Processing...</span>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            {/* Input Area */}
            <form onSubmit={handleSubmit} className="p-2 border-t border-zinc-800 bg-zinc-900/30 flex items-center gap-2">
                <span className="text-emerald-500 font-bold">{'>'}</span>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    className="flex-1 bg-transparent border-none outline-none text-zinc-200 placeholder-zinc-700 font-mono"
                    placeholder={error ? "CONNECTION UNAVAILABLE" : ready ? "ENTER MESSAGE..." : "CONNECTING..."}
                    autoFocus
                    disabled={!ready || isLoading}
                />
                <div className={`w-2 h-4 ${isLoading ? 'bg-amber-500' : 'bg-emerald-500'} animate-pulse`} />
            </form>
        </div>
    );
};

export default Terminal;
