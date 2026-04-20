import React, { useEffect } from 'react';
import InspectionDeck from './InspectionDeck';
import { trackAgentView } from '@/lib/analytics';

const AgentPageClient = ({ agent }) => {
  useEffect(() => {
    if (agent?.id) trackAgentView(agent);
  }, [agent]);

  const handleClose = () => {
    window.location.href = '/';
  };

  return <InspectionDeck agent={agent} onClose={handleClose} />;
};

export default AgentPageClient;
