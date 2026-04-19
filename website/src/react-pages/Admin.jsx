import React, { useState } from 'react';
import { api } from '@/lib/api';

const Admin = () => {
    const [key, setKey] = useState('');
    const [flags, setFlags] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);

    const load = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await api.listFlags(key);
            setFlags(data.flags || []);
        } catch (e) {
            setError(e.message || 'Failed to load flags');
            setFlags(null);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-zinc-950 text-zinc-200 font-mono p-8">
            <h1 className="text-lg font-bold text-zinc-100 uppercase tracking-widest mb-6">Admin — Flagged Agents</h1>
            <div className="flex gap-3 mb-8">
                <input
                    type="password"
                    value={key}
                    onChange={e => setKey(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && load()}
                    placeholder="Admin API key"
                    className="bg-zinc-900 border border-zinc-700 text-zinc-200 text-sm px-3 py-1.5 w-64"
                />
                <button
                    onClick={load}
                    disabled={loading}
                    className="bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs uppercase tracking-wider px-4 py-1.5 border border-zinc-600"
                >
                    {loading ? 'Loading...' : 'Load'}
                </button>
            </div>
            {error && <p className="text-red-400 text-xs mb-4">{error}</p>}
            {flags !== null && (
                flags.length === 0 ? (
                    <p className="text-zinc-500 text-xs">No flags recorded.</p>
                ) : (
                    <table className="w-full text-xs border-collapse">
                        <thead>
                            <tr className="text-zinc-500 uppercase text-[10px] tracking-widest border-b border-zinc-800">
                                <th className="text-left py-2 pr-4">Agent</th>
                                <th className="text-left py-2 pr-4">Reason</th>
                                <th className="text-left py-2 pr-4">Details</th>
                                <th className="text-left py-2 pr-4">IP</th>
                                <th className="text-left py-2">Flagged At</th>
                            </tr>
                        </thead>
                        <tbody>
                            {flags.map(f => (
                                <tr key={f.id} className="border-b border-zinc-900 hover:bg-zinc-900/40">
                                    <td className="py-2 pr-4 text-zinc-300">{f.agent_name || f.agent_id}</td>
                                    <td className="py-2 pr-4 text-red-400">{f.reason}</td>
                                    <td className="py-2 pr-4 text-zinc-400 max-w-xs truncate">{f.details || '—'}</td>
                                    <td className="py-2 pr-4 text-zinc-500">{f.ip_address || '—'}</td>
                                    <td className="py-2 text-zinc-500">{new Date(f.flagged_at).toLocaleString()}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )
            )}
        </div>
    );
};

export default Admin;
