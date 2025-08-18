import React from 'react';

const IntegrationGuide = () => {
  return (
    <section className="mt-12 lg:mt-16">
      <div className="text-center mb-8">
        <h2 className="text-3xl lg:text-4xl font-bold text-white mb-4">
          Quick Integration Guide
        </h2>
        <p className="text-lg text-purple-200 max-w-3xl mx-auto">
          Get started with A2A agents in just a few steps
        </p>
      </div>
      
      <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20 text-center">
          <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center mx-auto mb-4 text-white font-bold text-xl">1</div>
          <h3 className="text-lg font-semibold text-white mb-2">Install Client</h3>
          <p className="text-purple-200 text-sm mb-3">Install the Python client library to access the registry</p>
          <div className="text-xs text-left">
            <div className="bg-black/30 rounded p-2 text-green-300 font-mono">
              <div>uv pip install a2a-registry-client</div>
              <div className="text-purple-300"># Or: pip install a2a-registry-client</div>
            </div>
          </div>
        </div>

        <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20 text-center">
          <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center mx-auto mb-4 text-white font-bold text-xl">2</div>
          <h3 className="text-lg font-semibold text-white mb-2">Browse Agents</h3>
          <p className="text-purple-200 text-sm mb-3">Explore the registry to find agents that match your requirements</p>
          <div className="text-xs text-left">
            <div className="bg-black/30 rounded p-2 text-green-300 font-mono">
              <div>• Web: a2aregistry.org</div>
              <div>• API: /registry.json</div>
            </div>
          </div>
        </div>

        <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20 text-center">
          <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center mx-auto mb-4 text-white font-bold text-xl">3</div>
          <h3 className="text-lg font-semibold text-white mb-2">Get Agent Details</h3>
          <p className="text-purple-200 text-sm mb-3">Use the registry client to get agent details and capabilities</p>
          <div className="text-xs text-left">
            <div className="bg-black/30 rounded p-2 text-green-300 font-mono">
              <div>registry = Registry()</div>
              <div>agents = registry.get_all()</div>
            </div>
          </div>
        </div>

        <div className="bg-white/10 backdrop-blur-sm rounded-xl p-6 border border-white/20 text-center">
          <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center mx-auto mb-4 text-white font-bold text-xl">4</div>
          <h3 className="text-lg font-semibold text-white mb-2">Connect & Interact</h3>
          <p className="text-purple-200 text-sm mb-3">Send requests to the agent using the A2A Protocol standard</p>
          <div className="text-xs text-left">
            <div className="bg-black/30 rounded p-2 text-green-300 font-mono">
              <div>requests.post(agent.url, </div>
              <div>&nbsp;&nbsp;json={"{"}"method": "hello"{"}"}</div>
              <div>)</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default IntegrationGuide;
