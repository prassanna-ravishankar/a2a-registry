import React, { useState, useEffect, useRef } from 'react';

const API_BASE = import.meta.env.PUBLIC_API_URL || '/api';

const Terminal = ({ agent, autoFocusInput = true }) => {
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
            { type: 'system', content: `Connected to ${agent.name} through the registry proxy.`, timestamp: now },
            { type: 'system', content: `Protocol A2A v${agent.protocolVersion || agent.version || '0.3'}`, timestamp: now },
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
                { type: 'error', content: `Error: ${err.message}`, timestamp: new Date() },
            ]);
        } finally {
            setIsLoading(false);
        }
    };

    const getLogStyle = (type) => `terminal-log--${type}`;

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
        <div className="agent-terminal">
            {/* Terminal Header */}
            <div className="agent-terminal__header">
                <span>Message exchange</span><span>{error ? 'Unavailable' : ready ? 'Ready' : 'Connecting'}</span>
            </div>

            {/* Logs Area */}
            <div className="agent-terminal__logs">
                {displayLogs.map((log, i) => (
                    <div key={i} className={`agent-terminal__line ${getLogStyle(log.type)}`}>
                        <span>[{log.timestamp?.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' }) || '--:--:--'}]</span>
                        <strong>{getPrefix(log.type)}</strong><span>{log.content}</span>
                    </div>
                ))}
                {isLoading && (
                    <div className="agent-terminal__line">
                        <span>[{new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span><strong>--</strong><span>Processing…</span>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            {/* Input Area */}
            <form onSubmit={handleSubmit} className="agent-terminal__input">
                <span>{'>'}</span>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    className="agent-terminal__field"
                    placeholder="Type a message"
                    autoFocus={autoFocusInput}
                    disabled={!ready || isLoading}
                />
                <button type="submit" disabled={!ready || isLoading}>Send</button>
            </form>
        </div>
    );
};

export default Terminal;
