import React from 'react';
import EvidenceLadder from './EvidenceLadder';
import { agentProvider } from '@/lib/utils';

function checkedAt(agent) {
  const raw = agent.last_health_check || agent.task_conformance?.checked_at;
  if (!raw) return 'Not checked';
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return 'Not checked';
  const elapsed = Date.now() - date.getTime();
  const minutes = Math.max(0, Math.floor(elapsed / 60000));
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? '' : 's'} ago`;
}

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
        <time dateTime={lastChecked || undefined} title={lastChecked ? new Date(lastChecked).toLocaleString() : undefined}>{checkedAt(agent)}</time>
      </span>
      <span className="agent-row__arrow" aria-hidden="true">↗</span>
    </a>
  );
}
