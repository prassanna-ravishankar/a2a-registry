import React from 'react';
import { ChevronDown } from 'lucide-react';

const FAQ = () => {
  return (
    <section className="mt-12 lg:mt-16">
      <div className="text-center mb-8">
        <h2 className="text-3xl lg:text-4xl font-bold mb-4">
          Frequently Asked Questions
        </h2>
        <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
          Everything you need to know about A2A Registry and integrating AI agents
        </p>
      </div>

      <div className="max-w-4xl mx-auto space-y-4">
        <details className="group bg-white/80 backdrop-blur-sm rounded-xl border border-purple-100 overflow-hidden shadow-sm hover:shadow-md transition-all">
          <summary className="p-6 cursor-pointer hover:bg-purple-50/50 transition-colors flex items-center justify-between">
            <h3 className="text-xl font-semibold inline-flex items-center">
              What is A2A Registry?
            </h3>
          </summary>
          <div className="px-6 pb-6 text-muted-foreground leading-relaxed border-t border-purple-100">
            <p className="mt-4">A2A Registry is a community-driven, open-source directory of AI agents using the A2A Protocol. <strong className="text-foreground">Unlike other registries that index code repositories or implementations, we exclusively index live, hosted agents that are actively running and accessible.</strong> Using a "Git as a Database" model, we leverage GitHub for transparent data submission, validation, and hosting.</p>
            <p className="mt-3">The registry is accessible both to humans via our website and to agents programmatically via a static API endpoint at <code className="bg-purple-100 px-2 py-1 rounded text-purple-700 font-mono text-sm">https://www.a2aregistry.org/registry.json</code></p>
          </div>
        </details>

        <details className="group bg-white/80 backdrop-blur-sm rounded-xl border border-purple-100 overflow-hidden shadow-sm hover:shadow-md transition-all">
          <summary className="p-6 cursor-pointer hover:bg-purple-50/50 transition-colors flex items-center justify-between">
            <h3 className="text-xl font-semibold inline-flex items-center">
              How do I connect to A2A agents?
            </h3>
          </summary>
          <div className="px-6 pb-6 text-muted-foreground leading-relaxed border-t border-purple-100">
            <p className="mt-4">There are multiple ways to access A2A agents:</p>

            <p className="mt-3 font-semibold text-foreground">Via Python Client (Recommended):</p>
            <pre className="bg-purple-50 rounded-lg p-4 mt-2 mb-3 text-purple-700 text-sm overflow-x-auto font-mono">pip install a2a-registry-client</pre>

            <p className="mt-3 font-semibold text-foreground">Via API:</p>
            <pre className="bg-purple-50 rounded-lg p-4 mt-2 mb-3 text-purple-700 text-sm overflow-x-auto font-mono">curl https://www.a2aregistry.org/registry.json</pre>

            <p>The registry provides agent URLs, capabilities, and integration examples for each agent. Each agent card shows detailed code examples for different integration patterns.</p>
          </div>
        </details>

        <details className="group bg-white/80 backdrop-blur-sm rounded-xl border border-purple-100 overflow-hidden shadow-sm hover:shadow-md transition-all">
          <summary className="p-6 cursor-pointer hover:bg-purple-50/50 transition-colors flex items-center justify-between">
            <h3 className="text-xl font-semibold inline-flex items-center">
              What is the A2A Protocol?
            </h3>
          </summary>
          <div className="px-6 pb-6 text-muted-foreground leading-relaxed border-t border-purple-100">
            <p className="mt-4">The A2A (Agent-to-Agent) Protocol is a standardized communication protocol that enables AI agents to interact with each other seamlessly. It defines how agents expose their capabilities, handle requests, and maintain interoperability. The protocol ensures that agents can discover each other's capabilities and communicate effectively regardless of their underlying implementation.</p>
            <p className="mt-3">Learn more at the <a href="https://a2a-protocol.org/latest/specification/" className="text-purple-600 hover:text-purple-700 underline" target="_blank" rel="noopener noreferrer">Official A2A Protocol Specification</a>.</p>
          </div>
        </details>

        <details className="group bg-white/80 backdrop-blur-sm rounded-xl border border-purple-100 overflow-hidden shadow-sm hover:shadow-md transition-all">
          <summary className="p-6 cursor-pointer hover:bg-purple-50/50 transition-colors flex items-center justify-between">
            <h3 className="text-xl font-semibold inline-flex items-center">
              How can I submit my agent to the registry?
            </h3>
          </summary>
          <div className="px-6 pb-6 text-muted-foreground leading-relaxed border-t border-purple-100">
            <p className="mt-4"><strong className="text-foreground">Important:</strong> We only accept live, hosted agents that are publicly accessible. Your agent must be deployed and operational before submission.</p>

            <div className="mt-3">
              <p className="font-semibold text-foreground">Requirements:</p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-sm">
                <li>A2A Protocol compliant with a valid <code className="bg-purple-100 px-1 rounded text-purple-700 font-mono">.well-known/agent.json</code> endpoint</li>
                <li>Live and responding to A2A Protocol requests</li>
                <li>Follow the <a href="https://a2a-protocol.org/latest/specification/#55-agentcard-object-structure" className="text-purple-600 hover:text-purple-700 underline" target="_blank" rel="noopener noreferrer">Official A2A AgentCard specification</a></li>
              </ul>
            </div>

            <div className="mt-3">
              <p className="font-semibold text-foreground">Submission Process:</p>
              <ol className="list-decimal list-inside mt-2 space-y-1 text-sm">
                <li>Fork the <a href="https://github.com/prassanna-ravishankar/a2a-registry" className="text-purple-600 hover:text-purple-700 underline" target="_blank" rel="noopener noreferrer">A2A Registry repository</a></li>
                <li>Create a JSON file in <code className="bg-purple-100 px-1 rounded text-purple-700 font-mono">/agents/</code> directory</li>
                <li>Submit a Pull Request</li>
                <li>Our CI will validate your submission</li>
              </ol>
            </div>

            <p className="mt-3">See the <a href="https://github.com/prassanna-ravishankar/a2a-registry/blob/main/CONTRIBUTING.md" className="text-purple-600 hover:text-purple-700 underline" target="_blank" rel="noopener noreferrer">Contributing Guide</a> for detailed instructions.</p>
          </div>
        </details>

        <details className="group bg-white/80 backdrop-blur-sm rounded-xl border border-purple-100 overflow-hidden shadow-sm hover:shadow-md transition-all">
          <summary className="p-6 cursor-pointer hover:bg-purple-50/50 transition-colors flex items-center justify-between">
            <h3 className="text-xl font-semibold inline-flex items-center">
              Are the agents in A2A Registry free to use?
            </h3>
          </summary>
          <div className="px-6 pb-6 text-muted-foreground leading-relaxed border-t border-purple-100">
            <p className="mt-4">Most agents in the registry are free for demonstration and testing purposes. Each agent has its own pricing model detailed in its specifications. The registry itself and the Python client are completely free and open source. You can check each agent's pricing details in their individual cards.</p>
          </div>
        </details>
      </div>
    </section>
  );
};

export default FAQ;
