export function rowAgent(agent) {
  const fields = ['id', 'name', 'author', 'provider', 'protocolVersion', 'uptime_percentage', 'is_healthy', 'conformance', 'task_conformance', 'last_health_check', 'wellKnownURI'];
  return { ...Object.fromEntries(fields.map((key) => [key, agent[key]])), description: String(agent.description || '').slice(0, 300), tags: agent.tags || [...new Set((agent.skills || []).flatMap((skill) => skill.tags || []))] };
}

export function lastSweep(agents) {
  const times = agents.map((agent) => Date.parse(agent.last_health_check)).filter(Number.isFinite);
  return times.length ? new Date(Math.max(...times)).toISOString() : null;
}

export function relativeCheck(value) {
  const time = Date.parse(value);
  if (!Number.isFinite(time)) return 'not checked';
  const minutes = Math.max(0, Math.floor((Date.now() - time) / 60000));
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)} hr ago`;
  return `${Math.floor(minutes / 1440)} days ago`;
}
