import React, { useState } from 'react';
import { Send, CheckCircle2, XCircle, Loader2, ExternalLink } from 'lucide-react';
import { api } from '../lib/api';
import { trackAgentSubmission } from '../lib/analytics';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

const SubmitForm = () => {
  const [wellKnownURI, setWellKnownURI] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  const [submittedAgent, setSubmittedAgent] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const result = await api.registerAgentByURI(wellKnownURI);
      setSuccess(true);
      setSubmittedAgent(result);
      trackAgentSubmission(true, result.name);
      setWellKnownURI('');
    } catch (err) {
      setError(err.message || 'Failed to register agent');
      trackAgentSubmission(false, null);
    } finally {
      setLoading(false);
    }
  };

  if (success && submittedAgent) {
    return (
      <div className="border border-emerald-500/30 bg-emerald-500/5 p-6">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="text-[10px] text-emerald-500 uppercase tracking-wider mb-1">
              REGISTRATION_COMPLETE
            </div>
            <h3 className="text-lg font-bold text-zinc-100 mb-2">
              {submittedAgent.name}
            </h3>
            <p className="text-sm text-zinc-400 mb-4">
              Agent is now live on the registry and discoverable by other agents.
            </p>
            <div className="flex gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setSuccess(false);
                  setSubmittedAgent(null);
                }}
                className="text-xs border-zinc-700 hover:border-emerald-500/50 hover:text-emerald-400"
              >
                Register another
              </Button>
              <a href="/">
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-xs text-zinc-400 hover:text-zinc-100"
                >
                  View registry
                </Button>
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="wellKnownURI"
            className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-2"
          >
            WELL_KNOWN_URI
          </label>
          <Input
            type="url"
            id="wellKnownURI"
            value={wellKnownURI}
            onChange={(e) => setWellKnownURI(e.target.value)}
            placeholder="https://example.com/.well-known/agent.json"
            required
            disabled={loading}
            className="h-10 bg-zinc-900 border-zinc-800 text-zinc-200 text-sm font-mono focus:border-emerald-500/50 focus:ring-0 placeholder:text-zinc-600"
          />
          <p className="mt-2 text-[10px] text-zinc-600">
            Must end with /.well-known/agent.json or /.well-known/agent-card.json
          </p>
        </div>

        {error && (
          <div className="border border-red-500/30 bg-red-500/5 p-4">
            <div className="flex items-start gap-3">
              <XCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-[10px] text-red-500 uppercase tracking-wider mb-1">
                  ERROR
                </div>
                <p className="text-sm text-zinc-300">{error}</p>
              </div>
            </div>
          </div>
        )}

        <Button
          type="submit"
          disabled={loading || !wellKnownURI}
          className="w-full h-10 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-black font-bold text-sm"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              REGISTERING...
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <Send className="w-4 h-4" />
              REGISTER_AGENT
            </span>
          )}
        </Button>
      </form>

      {/* Requirements */}
      <div className="border-t border-zinc-800 pt-6">
        <h3 className="text-[10px] text-zinc-500 uppercase tracking-wider mb-4">
          REQUIREMENTS
        </h3>
        <ul className="space-y-3 text-sm text-zinc-400">
          <li className="flex items-start gap-3">
            <span className="text-emerald-500/70 text-xs mt-0.5">01</span>
            <span>Agent must be deployed and accessible via the provided URL</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-emerald-500/70 text-xs mt-0.5">02</span>
            <span>
              Must serve a valid{' '}
              <a
                href="https://a2a-protocol.org/latest/specification/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-500 hover:text-emerald-400 inline-flex items-center gap-1"
              >
                A2A Protocol agent card
                <ExternalLink className="w-3 h-3" />
              </a>
            </span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-emerald-500/70 text-xs mt-0.5">03</span>
            <span>Required fields: name, description, url, version, capabilities</span>
          </li>
        </ul>
      </div>
    </div>
  );
};

export default SubmitForm;
