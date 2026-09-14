import React, { useMemo, useState } from 'react';
import { api } from '@/lib/api';

export function CopyTabs({ snippets }) {
  const entries = Object.entries(snippets);
  const [active, setActive] = useState(entries[0]?.[0]);
  const [copied, setCopied] = useState(false);
  const value = snippets[active] || '';
  async function copy() {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }
  return <div className="copy-tabs"><div className="copy-tabs__bar">{entries.map(([key]) => <button key={key} type="button" aria-pressed={active === key} onClick={() => setActive(key)}>{key}</button>)}<button className="copy-action" type="button" onClick={copy}>{copied ? 'Copied' : 'Copy'}</button></div><pre><code>{value}</code></pre><span className="sr-only" aria-live="polite">{copied ? 'Snippet copied' : ''}</span></div>;
}

export function JsonCopy({ value }) {
  const json = useMemo(() => JSON.stringify(value, null, 2), [value]);
  const [copied, setCopied] = useState(false);
  return <><button type="button" className="text-action" onClick={async () => { await navigator.clipboard.writeText(json); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>{copied ? 'Copied JSON' : 'Copy JSON'}</button><span className="sr-only" aria-live="polite">{copied ? 'JSON copied' : ''}</span></>;
}

export function ReportAgent({ agentId }) {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState('idle');
  const [reason, setReason] = useState('harmful');
  const [details, setDetails] = useState('');
  if (!open) return <button type="button" className="text-action caveat" onClick={() => setOpen(true)}>Report this listing</button>;
  return <form className="report-form" onSubmit={async (event) => { event.preventDefault(); setState('sending'); try { await api.flagAgent(agentId, reason, details); setState('sent'); } catch { setState('error'); } }}><label><span>Reason</span><select value={reason} onChange={(event) => setReason(event.target.value)}><option value="harmful">Potentially harmful</option><option value="spam">Spam</option><option value="impersonation">Impersonation</option><option value="other">Other</option></select></label><label><span>Details</span><textarea value={details} onChange={(event) => setDetails(event.target.value)} rows="3" required /></label><div><button type="submit" disabled={state === 'sending' || state === 'sent'}>{state === 'sent' ? 'Report received' : state === 'sending' ? 'Sending…' : 'Send report'}</button><button type="button" onClick={() => setOpen(false)}>Cancel</button></div>{state === 'error' && <p className="caveat">The report could not be sent. Try again.</p>}</form>;
}
