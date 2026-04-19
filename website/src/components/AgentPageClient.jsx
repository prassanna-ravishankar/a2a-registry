import React, { useEffect, useState } from 'react';
import InspectionDeck from './InspectionDeck';
import { api } from '@/lib/api';
import { trackAgentView } from '@/lib/analytics';

const AgentPageClient = ({ agent: initial }) => {
  const [agent, setAgent] = useState(initial);

  useEffect(() => {
    if (initial?.id) trackAgentView(initial);
    let cancelled = false;
    (async () => {
      try {
        const fresh = await api.getAgent(initial.id);
        if (!cancelled && fresh) setAgent(fresh);
      } catch {
        // Use server-rendered snapshot if live fetch fails
      }
    })();
    return () => { cancelled = true; };
  }, [initial]);

  const handleClose = () => {
    window.location.href = '/';
  };

  return (
    <div className="border border-zinc-800">
      <InspectionDeck agent={agent} onClose={handleClose} />
    </div>
  );
};

export default AgentPageClient;
