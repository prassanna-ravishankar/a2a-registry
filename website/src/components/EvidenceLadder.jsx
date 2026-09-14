import React from 'react';
import { trustLevel, TRUST_LEVELS } from '@/lib/trust';

export default function EvidenceLadder({ agent, compact = false, className = '' }) {
  const trust = trustLevel(agent);
  const detail = TRUST_LEVELS.map((item, index) => `${item.label}: ${trust.evidence[index] ? 'yes' : 'no'}`).join(', ');

  return (
    <span
      className={`evidence-ladder ${compact ? 'evidence-ladder--compact' : ''} ${className}`.trim()}
      aria-label={`Evidence level: ${trust.label}. ${detail}`}
      title={detail}
    >
      <span className="evidence-ladder__marks" aria-hidden="true">
        {TRUST_LEVELS.map((item, index) => (
          <span
            key={item.key}
            className={`evidence-ladder__mark ${trust.evidence[index] ? 'is-filled' : ''} ${index === 1 && agent?.conformance === false ? 'is-caveat' : ''}`}
          />
        ))}
      </span>
      <span className="evidence-ladder__label">{trust.label}</span>
    </span>
  );
}
