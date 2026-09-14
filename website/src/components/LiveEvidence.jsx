import React, { useEffect, useState } from 'react';
import EvidenceLadder from './EvidenceLadder';
import { api } from '@/lib/api';
import { relativeCheck } from '@/lib/registryView';

export default function LiveEvidence({ initialAgent }) {
  const [agent, setAgent] = useState(initialAgent);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    api.getAgent(initialAgent.id).then((value) => { if (active) setAgent(value); }).catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [initialAgent.id]);
  const checked = agent.last_health_check;
  return <div aria-live="polite"><EvidenceLadder agent={agent} /><p className="mono checked-at">Last sweep <time dateTime={checked || undefined} title={checked || undefined}>{relativeCheck(checked)}</time></p>{failed && <p className="page-status">Live evidence unavailable. Showing saved observations.</p>}</div>;
}
