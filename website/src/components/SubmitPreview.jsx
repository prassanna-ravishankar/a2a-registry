import React, { useState } from 'react';
import EvidenceLadder from './EvidenceLadder';
import { api } from '@/lib/api';

export default function SubmitPreview() {
  const [uri, setUri] = useState('');
  const [preview, setPreview] = useState(null);
  const [state, setState] = useState('idle');
  const [error, setError] = useState('');

  async function inspect(event) {
    event.preventDefault();
    setState('previewing'); setError(''); setPreview(null);
    try {
      const result = await api.previewAgentByURI(uri);
      setPreview({ ...result.agent, id: `preview:${uri}`, conformance: result.evidence.conformant, conformance_errors: result.evidence.errors || [] });
      setState('ready');
    } catch (problem) {
      setError(problem.message || 'The Agent Card could not be inspected.');
      setState('error');
    }
  }

  async function register() {
    setState('registering'); setError('');
    try {
      const agent = await api.registerAgentByURI(uri);
      window.location.assign(`/agents/${agent.id}`);
    } catch (problem) {
      setError(problem.message || 'Registration failed.');
      setState('ready');
    }
  }

  return <div className="submit-flow">
    <form className="submit-inspector" onSubmit={inspect}>
      <label htmlFor="well-known-uri">Canonical Agent Card URL</label>
      <div className="submit-input-row">
        <input id="well-known-uri" type="url" value={uri} onChange={(event) => { setUri(event.target.value); setPreview(null); setState('idle'); }} placeholder="https://agent.example/.well-known/agent-card.json" required />
        <button type="submit" disabled={state === 'previewing'}>{state === 'previewing' ? 'Fetching…' : 'Inspect card'}</button>
      </div>
      <p>Fetching is read-only. Registration happens only after you review the evidence below.</p>
    </form>
    {error && <p className="submit-error" role="alert">{error}</p>}
    {preview && <section className="submit-preview" aria-live="polite">
      <div className="submit-preview__head"><div><span>Preview</span><h2>{preview.name}</h2><p>{preview.provider?.organization || preview.author || 'Provider not declared'}</p></div><EvidenceLadder agent={preview} /></div>
      <dl className="datasheet"><div><dt>Canonical URL</dt><dd><code>{preview.wellKnownURI}</code></dd></div><div><dt>Protocol version</dt><dd><code>{preview.protocolVersion}</code></dd></div><div><dt>Endpoint</dt><dd><code>{preview.url}</code></dd></div><div><dt>Skills declared</dt><dd><code>{preview.skills?.length || 0}</code></dd></div></dl>
      <ul className="caveat">{preview.conformance_errors.map((reason, index) => <li key={index}>{reason}</li>)}</ul>
      <p className="submit-caveat">Reachability and task verification are established by the registration probe and subsequent health sweeps.</p>
      <button type="button" onClick={register} disabled={state === 'registering'}>{state === 'registering' ? 'Registering and probing…' : 'Register this agent'}</button>
    </section>}
  </div>;
}
