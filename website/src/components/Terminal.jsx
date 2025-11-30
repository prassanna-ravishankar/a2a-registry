import React, { useState, useEffect, useRef } from 'react';
import { fetchAgentCard, getAgentEndpoint, sendMessage, pollTask, extractMessageText, extractTaskText } from '../utils/a2aClient';

const Terminal = ({ agent }) => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [agentConfig, setAgentConfig] = useState(null); // {url, transport}
    const [error, setError] = useState(null);
    const [contextId, setContextId] = useState(null); // Maintain context for chat session
    const bottomRef = useRef(null);

    // Initial system logs (each log should have: { type, content, timestamp })
    const [systemLogs, setSystemLogs] = useState([]);

    // Fetch agent card and endpoint when agent changes
    useEffect(() => {
        const initializeAgent = async () => {
            const now = new Date();
            setSystemLogs([
                { type: 'system', content: `INITIALIZING CONNECTION TO ${agent.name.toUpperCase()}...`, timestamp: now },
                { type: 'system', content: `PROTOCOL: A2A v${agent.protocolVersion || agent.version || '0.3'}`, timestamp: now }
            ]);
            setMessages([]);
            setError(null);
            setAgentConfig(null);
            // Generate new contextId for this chat session
            setContextId(crypto.randomUUID());

            try {
                let config;

                // Try to fetch agent card from wellKnownURI
                try {
                    const agentCard = await fetchAgentCard(agent.wellKnownURI);
                    config = getAgentEndpoint(agentCard);
                    setSystemLogs(prev => [
                        ...prev,
                        { type: 'info', content: 'AGENT CARD FETCHED SUCCESSFULLY.', timestamp: new Date() }
                    ]);
                } catch (cardError) {
                    // Fallback to registry data if agent card fetch fails
                    console.warn('Agent card fetch failed, using registry data:', cardError);
                    config = {
                        url: agent.url,
                        transport: agent.preferredTransport || 'JSONRPC'
                    };
                    setSystemLogs(prev => [
                        ...prev,
                        { type: 'info', content: 'USING REGISTRY DATA (AGENT CARD UNAVAILABLE).', timestamp: new Date() }
                    ]);
                }

                setAgentConfig(config);

                const connectedTime = new Date();
                setSystemLogs(prev => [
                    ...prev,
                    { type: 'success', content: 'CONNECTION ESTABLISHED.', timestamp: connectedTime },
                    { type: 'info', content: `ENDPOINT: ${config.url}`, timestamp: connectedTime },
                    { type: 'info', content: `TRANSPORT: ${config.transport}`, timestamp: connectedTime },
                    { type: 'info', content: 'TYPE YOUR MESSAGE OR ASK A QUESTION.', timestamp: connectedTime }
                ]);
            } catch (err) {
                console.error('Failed to initialize agent:', err);
                const errorTime = new Date();
                setSystemLogs(prev => [
                    ...prev,
                    { type: 'error', content: `CONNECTION FAILED: ${err.message}`, timestamp: errorTime },
                    { type: 'info', content: 'This agent may not support browser-based communication (CORS).', timestamp: errorTime }
                ]);
                setError(err.message);
            }
        };

        initializeAgent();
    }, [agent]);

    // Auto-scroll
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, systemLogs]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim() || !agentConfig || isLoading) return;

        const userMessage = input;
        setInput('');
        setIsLoading(true);

        // Add user message
        const newUserMsg = { type: 'request', content: userMessage, timestamp: new Date() };
        setMessages(prev => [...prev, newUserMsg]);

        try {
            // Send message to agent
            const response = await sendMessage(agentConfig.url, userMessage, {
                streaming: false,
                acceptedOutputModes: agent.defaultOutputModes || ['text/plain', 'application/json'],
                transport: agentConfig.transport,
                contextId: contextId // Pass the session contextId
            });

            // Parse response
            let responseText = '';

            if (response.message) {
                // Direct message response
                responseText = extractMessageText(response.message);
            } else if (response.id) {
                // Task response - need to poll until completed
                const taskId = response.id;
                const taskState = response.status?.state;

                // If task is not already completed, poll it
                if (taskState !== 'completed' && taskState !== 'failed') {
                    setMessages(prev => [...prev, { type: 'info', content: `Task ${taskState || 'submitted'}, waiting for completion...`, timestamp: new Date() }]);

                    const completedTask = await pollTask(
                        agentConfig.url,
                        taskId,
                        agentConfig.transport,
                        (task) => {
                            // Optional: update UI with task status changes
                            console.log('Task status update:', task.status?.state);
                        }
                    );

                    responseText = extractTaskText(completedTask);
                } else {
                    // Task already completed
                    responseText = extractTaskText(response);
                }
            } else {
                responseText = 'No response from agent';
            }

            setMessages(prev => [...prev, { type: 'response', content: responseText, timestamp: new Date() }]);
        } catch (err) {
            console.error('Failed to send message:', err);
            setMessages(prev => [
                ...prev,
                {
                    type: 'error',
                    content: `ERROR: ${err.message}. This agent may not support browser-based requests (CORS).`,
                    timestamp: new Date()
                }
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
                    <div className={`w-2 h-2 rounded-full ${error ? 'bg-red-500' : agentConfig ? 'bg-emerald-500' : 'bg-amber-500'}`} />
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
                    placeholder={error ? "CONNECTION UNAVAILABLE" : agentConfig ? "ENTER MESSAGE..." : "CONNECTING..."}
                    autoFocus
                    disabled={!agentConfig || isLoading}
                />
                <div className={`w-2 h-4 ${isLoading ? 'bg-amber-500' : 'bg-emerald-500'} animate-pulse`} />
            </form>
        </div>
    );
};

export default Terminal;
