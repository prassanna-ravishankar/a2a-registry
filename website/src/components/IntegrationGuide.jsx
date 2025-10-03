import React from 'react';

const IntegrationGuide = () => {
  return (
    <section className="mt-12 lg:mt-16">
      <div className="text-center mb-8">
        <h2 className="text-3xl lg:text-4xl font-bold mb-4">
          Quick Integration Guide
        </h2>
        <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
          Get started with A2A agents in just a few steps
        </p>
      </div>

      <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-purple-100 text-center shadow-sm hover:shadow-md transition-all">
          <div className="w-12 h-12 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-4 text-white font-bold text-xl">1</div>
          <h3 className="text-lg font-semibold mb-2">Install Client</h3>
          <p className="text-muted-foreground text-sm mb-3">Install the Python client library to access the registry</p>
          <div className="text-xs text-left">
            <div className="bg-purple-50 rounded p-2 font-mono">
              <div className="text-purple-700">uv pip install a2a-registry-client</div>
              <div className="text-purple-500"># Or: pip install a2a-registry-client</div>
            </div>
          </div>
        </div>

        <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-purple-100 text-center shadow-sm hover:shadow-md transition-all">
          <div className="w-12 h-12 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-4 text-white font-bold text-xl">2</div>
          <h3 className="text-lg font-semibold mb-2">Browse Agents</h3>
          <p className="text-muted-foreground text-sm mb-3">Explore the registry to find agents that match your requirements</p>
          <div className="text-xs text-left">
            <div className="bg-purple-50 rounded p-2 font-mono">
              <div className="text-purple-700">• Web: a2aregistry.org</div>
              <div className="text-purple-700">• API: /registry.json</div>
            </div>
          </div>
        </div>

        <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-purple-100 text-center shadow-sm hover:shadow-md transition-all">
          <div className="w-12 h-12 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-4 text-white font-bold text-xl">3</div>
          <h3 className="text-lg font-semibold mb-2">Get Agent Details</h3>
          <p className="text-muted-foreground text-sm mb-3">Use the registry client to get agent details and capabilities</p>
          <div className="text-xs text-left">
            <div className="bg-purple-50 rounded p-2 font-mono">
              <div className="text-purple-700">registry = Registry()</div>
              <div className="text-purple-700">agents = registry.get_all()</div>
            </div>
          </div>
        </div>

        <div className="bg-white/80 backdrop-blur-sm rounded-xl p-6 border border-purple-100 text-center shadow-sm hover:shadow-md transition-all">
          <div className="w-12 h-12 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-4 text-white font-bold text-xl">4</div>
          <h3 className="text-lg font-semibold mb-2">Connect & Interact</h3>
          <p className="text-muted-foreground text-sm mb-3">Send requests to the agent using the A2A Protocol standard</p>
          <div className="text-xs text-left">
            <div className="bg-purple-50 rounded p-2 font-mono">
              <div className="text-purple-700">requests.post(agent.url, </div>
              <div className="text-purple-700">&nbsp;&nbsp;json={"{"}"method": "hello"{"}"}</div>
              <div className="text-purple-700">)</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default IntegrationGuide;
