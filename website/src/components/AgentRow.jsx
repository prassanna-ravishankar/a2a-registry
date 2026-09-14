import React from 'react';
import EvidenceLadder from './EvidenceLadder';
import { agentProvider } from '@/lib/utils';

import { relativeCheck } from '@/lib/registryView';

export default function AgentRow({ agent }) {
  const lastChecked = agent.last_health_check || agent.task_conformance?.checked_at;
  const uptime = Number.isFinite(Number(agent.uptime_percentage))
    ? `${Number(agent.uptime_percentage).toFixed(1)}%`
    : 'Unavailable';

  return (
    <a className="agent-row" href={`/agents/${encodeURIComponent(agent.id)}`}>
      <span className="agent-row__identity">
        <strong>{agent.name}</strong>
        <span>{agentProvider(agent)}</span>
      </span>
      <span className="agent-row__datum agent-row__protocol">
        <span className="agent-row__mobile-label">Protocol</span>
        {agent.protocolVersion || 'Unavailable'}
      </span>
      <span className="agent-row__datum">
        <span className="agent-row__mobile-label">Uptime</span>
        {uptime}
      </span>
      <EvidenceLadder agent={agent} compact />
      <span className="agent-row__checked">
        <span className="agent-row__mobile-label">Last checked</span>
        <time dateTime={lastChecked || undefined} title={lastChecked ? new Date(lastChecked).toLocaleString() : undefined}>{relativeCheck(lastChecked)}</time>
      </span>
      <span className="agent-row__arrow" aria-hidden="true">↗</span>
    </a>
  );
}
