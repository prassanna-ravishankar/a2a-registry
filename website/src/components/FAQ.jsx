import React from 'react';

const FAQ = () => {
  return (
    <section className="mt-12 lg:mt-16">
      <div className="text-center mb-8">
        <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">
          Frequently Asked Questions
        </h2>
        <p className="text-lg text-purple-200 max-w-3xl mx-auto">
          Everything you need to know about A2A Registry and integrating AI agents
        </p>
      </div>
      
      <div className="max-w-4xl mx-auto space-y-6">
        <details className="bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 overflow-hidden">
          <summary className="p-6 cursor-pointer hover:bg-white/5 transition-colors">
            <h3 className="text-xl font-semibold text-white inline">What is A2A Registry?</h3>
          </summary>
          <div className="px-6 pb-6 text-purple-200 leading-relaxed">
            <p>A2A Registry is a community-driven, open-source directory of AI agents using the A2A Protocol. <strong>Unlike other registries that index code repositories or implementations, we exclusively index live, hosted agents that are actively running and accessible.</strong> Using a "Git as a Database" model, we leverage GitHub for transparent data submission, validation, and hosting.</p>
            <p className="mt-3">The registry is accessible both to humans via our website and to agents programmatically via a static API endpoint at <code className="bg-black/30 px-2 py-1 rounded text-green-300">https://www.a2aregistry.org/registry.json</code></p>
          </div>
        </details>

        <details className="bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 overflow-hidden">
          <summary className="p-6 cursor-pointer hover:bg-white/5 transition-colors">
            <h3 className="text-xl font-semibold text-white inline">How do I connect to A2A agents?</h3>
          </summary>
          <div className="px-6 pb-6 text-purple-200 leading-relaxed">
            <p>There are multiple ways to access A2A agents:</p>
            
            <p className="mt-3 font-semibold">Via Python Client (Recommended):</p>
            <pre className="bg-black/30 rounded-lg p-4 mt-2 mb-3 text-green-300 text-sm overflow-x-auto">pip install a2a-registry-client</pre>
            
            <p className="mt-3 font-semibold">Via API:</p>
            <pre className="bg-black/30 rounded-lg p-4 mt-2 mb-3 text-green-300 text-sm overflow-x-auto">curl https://www.a2aregistry.org/registry.json</pre>
            
            <p>The registry provides agent URLs, capabilities, and integration examples for each agent. Each agent card shows detailed code examples for different integration patterns.</p>
          </div>
        </details>

        <details className="bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 overflow-hidden">
          <summary className="p-6 cursor-pointer hover:bg-white/5 transition-colors">
            <h3 className="text-xl font-semibold text-white inline">What is the A2A Protocol?</h3>
          </summary>
          <div className="px-6 pb-6 text-purple-200 leading-relaxed">
            <p>The A2A (Agent-to-Agent) Protocol is a standardized communication protocol that enables AI agents to interact with each other seamlessly. It defines how agents expose their capabilities, handle requests, and maintain interoperability. The protocol ensures that agents can discover each other's capabilities and communicate effectively regardless of their underlying implementation.</p>
            <p className="mt-3">Learn more at the <a href="https://a2a-protocol.org/latest/specification/" className="text-purple-400 hover:text-purple-300 underline" target="_blank" rel="noopener noreferrer">Official A2A Protocol Specification</a>.</p>
          </div>
        </details>

        <details className="bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 overflow-hidden">
          <summary className="p-6 cursor-pointer hover:bg-white/5 transition-colors">
            <h3 className="text-xl font-semibold text-white inline">How can I submit my agent to the registry?</h3>
          </summary>
          <div className="px-6 pb-6 text-purple-200 leading-relaxed">
            <p><strong>Important:</strong> We only accept live, hosted agents that are publicly accessible. Your agent must be deployed and operational before submission.</p>
            
            <div className="mt-3">
              <p className="font-semibold">Requirements:</p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-sm">
                <li>A2A Protocol compliant with a valid <code className="bg-black/30 px-1 rounded">.well-known/agent.json</code> endpoint</li>
                <li>Live and responding to A2A Protocol requests</li>
                <li>Follow the <a href="https://a2a-protocol.org/latest/specification/#55-agentcard-object-structure" className="text-purple-400 hover:text-purple-300 underline" target="_blank" rel="noopener noreferrer">Official A2A AgentCard specification</a></li>
              </ul>
            </div>
            
            <div className="mt-3">
              <p className="font-semibold">Submission Process:</p>
              <ol className="list-decimal list-inside mt-2 space-y-1 text-sm">
                <li>Fork the <a href="https://github.com/prassanna-ravishankar/a2a-registry" className="text-purple-400 hover:text-purple-300 underline" target="_blank" rel="noopener noreferrer">A2A Registry repository</a></li>
                <li>Create a JSON file in <code className="bg-black/30 px-1 rounded">/agents/</code> directory</li>
                <li>Submit a Pull Request</li>
                <li>Our CI will validate your submission</li>
              </ol>
            </div>
            
            <p className="mt-3">See the <a href="https://github.com/prassanna-ravishankar/a2a-registry/blob/main/CONTRIBUTING.md" className="text-purple-400 hover:text-purple-300 underline" target="_blank" rel="noopener noreferrer">Contributing Guide</a> for detailed instructions.</p>
          </div>
        </details>

        <details className="bg-white/10 backdrop-blur-sm rounded-xl border border-white/20 overflow-hidden">
          <summary className="p-6 cursor-pointer hover:bg-white/5 transition-colors">
            <h3 className="text-xl font-semibold text-white inline">Are the agents in A2A Registry free to use?</h3>
          </summary>
          <div className="px-6 pb-6 text-purple-200 leading-relaxed">
            <p>Most agents in the registry are free for demonstration and testing purposes. Each agent has its own pricing model detailed in its specifications. The registry itself and the Python client are completely free and open source. You can check each agent's pricing details in their individual cards.</p>
          </div>
        </details>
      </div>
    </section>
  );
};

export default FAQ;
