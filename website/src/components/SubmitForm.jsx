import React, { useState } from 'react';
import { Send, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { api } from '../lib/api';
import { trackAgentSubmission } from '../lib/analytics';

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
      // First fetch the agent data from the wellKnownURI
      const response = await fetch(wellKnownURI);
      if (!response.ok) {
        throw new Error(`Failed to fetch agent card: HTTP ${response.status}`);
      }

      const agentData = await response.json();

      // Add the wellKnownURI to the data
      agentData.wellKnownURI = wellKnownURI;

      // Submit to our API
      const result = await api.registerAgent(agentData);

      setSuccess(true);
      setSubmittedAgent(result);
      trackAgentSubmission(true, agentData.name);
      setWellKnownURI('');
    } catch (err) {
      setError(err.message || 'Failed to register agent');
      trackAgentSubmission(false, null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-black/40 border border-cyan-500/30 rounded-lg p-8 backdrop-blur-sm">
        <h2 className="text-2xl font-bold text-cyan-400 mb-6 font-mono">
          Register Your Agent
        </h2>

        {success && submittedAgent ? (
          <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-6 mb-6">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="w-6 h-6 text-green-400 flex-shrink-0 mt-1" />
              <div>
                <h3 className="text-lg font-bold text-green-400 mb-2">
                  Agent Registered Successfully!
                </h3>
                <p className="text-gray-300 mb-3">
                  <span className="font-mono text-cyan-400">
                    {submittedAgent.name}
                  </span>{' '}
                  is now live on the registry.
                </p>
                <button
                  onClick={() => {
                    setSuccess(false);
                    setSubmittedAgent(null);
                  }}
                  className="text-sm text-cyan-400 hover:text-cyan-300 font-mono"
                >
                  Register another agent →
                </button>
              </div>
            </div>
          </div>
        ) : (
          <>
            <p className="text-gray-300 mb-6">
              Submit your agent's{' '}
              <code className="text-cyan-400 bg-black/40 px-2 py-1 rounded">
                /.well-known/agent.json
              </code>{' '}
              URL. We'll verify ownership and register your agent instantly.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="wellKnownURI"
                  className="block text-sm font-mono text-gray-400 mb-2"
                >
                  Well-Known URI
                </label>
                <input
                  type="url"
                  id="wellKnownURI"
                  value={wellKnownURI}
                  onChange={(e) => setWellKnownURI(e.target.value)}
                  placeholder="https://example.com/.well-known/agent.json"
                  required
                  className="w-full bg-black/40 border border-cyan-500/30 rounded-lg px-4 py-3 text-gray-100 font-mono focus:border-cyan-400 focus:outline-none focus:ring-2 focus:ring-cyan-400/20"
                  disabled={loading}
                />
                <p className="mt-2 text-xs text-gray-500 font-mono">
                  Must end with /.well-known/agent.json or
                  /.well-known/agent-card.json
                </p>
              </div>

              {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm text-red-400 font-mono">{error}</p>
                    </div>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loading || !wellKnownURI}
                className="w-full bg-cyan-500 hover:bg-cyan-400 disabled:bg-gray-700 disabled:cursor-not-allowed text-black font-bold py-3 px-6 rounded-lg font-mono flex items-center justify-center gap-2 transition-colors"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Registering...
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5" />
                    Register Agent
                  </>
                )}
              </button>
            </form>

            <div className="mt-6 pt-6 border-t border-cyan-500/20">
              <h3 className="text-sm font-mono text-gray-400 mb-3">
                Requirements
              </h3>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-start gap-2">
                  <span className="text-cyan-400 mt-0.5">•</span>
                  <span>
                    Agent must be deployed and accessible via the provided URL
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-cyan-400 mt-0.5">•</span>
                  <span>Must serve valid A2A Protocol agent card</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-cyan-400 mt-0.5">•</span>
                  <span>
                    Name and description must match between submission and
                    well-known endpoint
                  </span>
                </li>
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default SubmitForm;
