import React from 'react';
import { ArrowLeft } from 'lucide-react';
import SubmitForm from '../components/SubmitForm';

const Submit = () => {
  return (
    <div className="min-h-screen bg-black text-zinc-200 font-mono">
      {/* Header */}
      <header className="h-12 border-b border-zinc-800 bg-zinc-950 flex items-center px-4 justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-zinc-900 border border-zinc-800 flex items-center justify-center">
            <img src="/logo.png" alt="A2A Registry" className="w-5 h-5" />
          </div>
          <h1 className="font-mono font-bold text-zinc-100 tracking-wider text-sm">
            A2A_REGISTRY <span className="text-zinc-600 text-xs font-normal">// SUBMIT</span>
          </h1>
        </div>

        <div className="flex items-center gap-4 text-[10px] font-mono text-zinc-500">
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            <span className="text-emerald-500">REGISTRY_ONLINE</span>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar-like area */}
        <div className="hidden md:block w-64 shrink-0 border-r border-zinc-800 bg-zinc-950/50 p-4">
          <a
            href="/"
            className="flex items-center gap-2 text-xs text-zinc-400 hover:text-emerald-400 transition-colors mb-6"
          >
            <ArrowLeft className="w-4 h-4" />
            BACK_TO_REGISTRY
          </a>

          <div className="space-y-4">
            <div>
              <h3 className="text-[10px] text-zinc-600 uppercase tracking-wider mb-2">
                PROCESS_FLOW
              </h3>
              <ol className="text-xs text-zinc-500 space-y-2">
                <li className="flex items-start gap-2">
                  <span className="text-emerald-500/70">01</span>
                  <span>Submit wellKnownURI</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-500/70">02</span>
                  <span>System validates agent card</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-500/70">03</span>
                  <span>Agent added to registry</span>
                </li>
              </ol>
            </div>
          </div>
        </div>

        {/* Main content */}
        <main className="flex-1 p-6 md:p-8">
          <div className="max-w-2xl mx-auto">
            {/* Page header */}
            <div className="mb-8">
              <div className="flex items-center gap-2 text-[10px] text-zinc-600 uppercase tracking-wider mb-2">
                <span className="text-emerald-500">&gt;</span>
                AGENT_REGISTRATION
              </div>
              <h2 className="text-xl font-bold text-zinc-100 mb-2">
                Register Your Agent
              </h2>
              <p className="text-sm text-zinc-500">
                Submit your agent's well-known URI to add it to the A2A Registry.
                We'll validate the agent card and make it discoverable.
              </p>
            </div>

            {/* Mobile back link */}
            <a
              href="/"
              className="md:hidden flex items-center gap-2 text-xs text-zinc-400 hover:text-emerald-400 transition-colors mb-6"
            >
              <ArrowLeft className="w-4 h-4" />
              BACK_TO_REGISTRY
            </a>

            <SubmitForm />
          </div>
        </main>
      </div>
    </div>
  );
};

export default Submit;
