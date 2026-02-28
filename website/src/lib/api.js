const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://www.a2aregistry.org/api';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      error.detail || `HTTP ${response.status}`,
      response.status,
      error
    );
  }

  return response.json();
}

export const api = {
  // Get all agents with optional filtering
  async getAgents({ skill, capability, author, search, conformance, limit = 50, offset = 0 } = {}) {
    const params = new URLSearchParams();
    if (skill) params.append('skill', skill);
    if (capability) params.append('capability', capability);
    if (author) params.append('author', author);
    if (search) params.append('search', search);
    if (conformance) params.append('conformance', conformance);
    params.append('limit', limit);
    params.append('offset', offset);

    return fetchAPI(`/agents?${params}`);
  },

  // Get single agent by ID
  async getAgent(agentId) {
    return fetchAPI(`/agents/${agentId}`);
  },

  // Get agent health status
  async getAgentHealth(agentId) {
    return fetchAPI(`/agents/${agentId}/health`);
  },

  // Get agent uptime metrics
  async getAgentUptime(agentId, periodDays = 30) {
    return fetchAPI(`/agents/${agentId}/uptime?period_days=${periodDays}`);
  },

  // Get registry statistics
  async getStats() {
    return fetchAPI('/stats');
  },

  // Register a new agent (full payload)
  async registerAgent(agentData) {
    return fetchAPI('/agents', {
      method: 'POST',
      body: JSON.stringify(agentData),
    });
  },

  // Register agent by wellKnownURI (simplified - backend fetches the agent card)
  async registerAgentByURI(wellKnownURI, author = null) {
    return fetchAPI('/agents/register', {
      method: 'POST',
      body: JSON.stringify({ wellKnownURI, author }),
    });
  },

  // Flag/report an agent
  async flagAgent(agentId, reason, details) {
    return fetchAPI(`/agents/${agentId}/flag`, {
      method: 'POST',
      body: JSON.stringify({ agent_id: agentId, reason, details: details || null }),
    });
  },

  // List flags (admin)
  async listFlags(adminKey, limit = 100, offset = 0) {
    return fetchAPI(`/admin/flags?limit=${limit}&offset=${offset}`, {
      headers: { 'X-Admin-Key': adminKey },
    });
  },
};

// Fallback: fetch from static registry.json (backward compatibility)
export async function fetchStaticRegistry() {
  const response = await fetch('/registry.json');
  if (!response.ok) {
    throw new Error('Failed to fetch static registry');
  }
  return response.json();
}
