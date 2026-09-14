export const TRUST_LEVELS = Object.freeze([
  { key: 'fetched', label: 'Fetched' },
  { key: 'conformant', label: 'Conformant' },
  { key: 'reachable', label: 'Reachable' },
  { key: 'task-verified', label: 'Task verified' },
]);

function hasRegistryRecord(agent) {
  return Boolean(agent?.id && agent?.wellKnownURI);
}

export function trustEvidence(agent) {
  return [
    hasRegistryRecord(agent),
    agent?.conformance === true,
    agent?.is_healthy === true,
    agent?.task_conformance?.passed === true,
  ];
}

export function trustLevel(agent) {
  const evidence = trustEvidence(agent);
  const level = evidence.reduce((highest, passed, index) => passed ? index + 1 : highest, 0);

  return {
    level,
    key: level === 0 ? 'unverified' : TRUST_LEVELS[level - 1].key,
    label: level === 0 ? 'Unverified' : TRUST_LEVELS[level - 1].label,
    evidence,
  };
}
