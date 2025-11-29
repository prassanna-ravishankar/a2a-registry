import React, { useState, useEffect, useRef } from 'react';

const Terminal = ({ agent }) => {
    const [logs, setLogs] = useState([]);
    const [input, setInput] = useState('');
    const bottomRef = useRef(null);

    useEffect(() => {
        // Initial connection simulation
        setLogs([
            { type: 'system', content: `INITIALIZING CONNECTION TO ${agent.name.toUpperCase()}...` },
            { type: 'system', content: `PROTOCOL: A2A v${agent.version}` },
            { type: 'success', content: 'CONNECTION ESTABLISHED.' },
            { type: 'info', content: 'TYPE "HELP" FOR AVAILABLE COMMANDS.' }
        ]);
    }, [agent]);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const handleCommand = (cmd) => {
        const command = cmd.trim().toLowerCase();
        let response = null;

        switch (command) {
            case 'help':
                response = { type: 'info', content: 'AVAILABLE COMMANDS: INFO, STATUS, SPECS, CONNECT, CLEAR' };
                break;
            case 'info':
                response = { type: 'response', content: agent.description.toUpperCase() };
                break;
            case 'status':
                response = { type: 'success', content: 'SYSTEM STATUS: ONLINE | LATENCY: <10ms | UPTIME: 99.9%' };
                break;
            case 'specs':
                response = { type: 'response', content: `PROVIDER: ${agent.author || 'UNKNOWN'} | LICENSE: ${agent.license || 'MIT'}` };
                break;
            case 'connect':
                response = { type: 'success', content: `INITIATING CONNECTION TO ${agent.url}...` };
                setTimeout(() => window.open(agent.url, '_blank'), 1000);
                break;
            case 'clear':
                setLogs([]);
                return;
            default:
                response = { type: 'error', content: `UNKNOWN COMMAND: "${command}". TYPE "HELP".` };
        }

        if (response) {
            setLogs(prev => [...prev, response]);
        }
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const newLog = { type: 'request', content: input };
        setLogs(prev => [...prev, newLog]);
        const currentInput = input;
        setInput('');

        // Process command
        setTimeout(() => {
            handleCommand(currentInput);
        }, 200);
    };

    const getLogStyle = (type) => {
        switch (type) {
            case 'request': return 'text-cyan-400';
            case 'response': return 'text-emerald-400';
            case 'system': return 'text-amber-500';
            case 'success': return 'text-emerald-500';
            case 'error': return 'text-red-500';
            default: return 'text-zinc-400';
        }
    };

    const getPrefix = (type) => {
        switch (type) {
            case 'request': return '>>';
            case 'response': return '<<';
            case 'system': return '!!';
            default: return '--';
        }
    };

    return (
        <div className="flex flex-col h-full bg-black border border-zinc-800 font-mono text-xs">
            {/* Terminal Header */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800 bg-zinc-900/50">
                <span className="text-zinc-400">TERMINAL_OUTPUT</span>
                <div className="flex gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-zinc-700" />
                    <div className="w-2 h-2 rounded-full bg-zinc-700" />
                    <div className="w-2 h-2 rounded-full bg-zinc-700" />
                </div>
            </div>

            {/* Logs Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-1 font-mono">
                {logs.map((log, i) => (
                    <div key={i} className="flex gap-2">
                        <span className="text-zinc-600 shrink-0">[{new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}]</span>
                        <span className={`font-bold shrink-0 w-6 ${getLogStyle(log.type)}`}>{getPrefix(log.type)}</span>
                        <span className={`${getLogStyle(log.type)} break-all`}>{log.content}</span>
                    </div>
                ))}
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
                    placeholder="ENTER COMMAND..."
                    autoFocus
                />
                <div className="w-2 h-4 bg-emerald-500 animate-pulse" />
            </form>
        </div>
    );
};

export default Terminal;
