import React from 'react';
import SubmitForm from '../components/SubmitForm';

const Submit = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-black via-gray-900 to-black py-12 px-6">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-cyan-400 mb-4 font-mono">
            Submit Your Agent
          </h1>
          <p className="text-gray-400 text-lg">
            Join the A2A Registry and make your agent discoverable
          </p>
        </div>

        <SubmitForm />

        <div className="mt-12 text-center">
          <a
            href="/"
            className="text-cyan-400 hover:text-cyan-300 font-mono text-sm"
          >
            ← Back to Registry
          </a>
        </div>
      </div>
    </div>
  );
};

export default Submit;
