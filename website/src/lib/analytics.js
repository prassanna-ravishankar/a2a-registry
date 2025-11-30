import posthog from 'posthog-js';

export const trackEvent = (eventName, properties = {}) => {
  if (typeof posthog !== 'undefined' && posthog.capture) {
    posthog.capture(eventName, properties);
  }
};

export const trackAgentView = (agent) => {
  trackEvent('agent_viewed', {
    agent_id: agent.id,
    agent_name: agent.name,
    agent_author: agent.author,
  });
};

export const trackSearch = (query, resultCount) => {
  trackEvent('search_performed', {
    query,
    result_count: resultCount,
  });
};

export const trackFilterChange = (filterType, value) => {
  trackEvent('filter_changed', {
    filter_type: filterType,
    value,
  });
};

export const trackAgentSubmission = (success, agent_name) => {
  trackEvent('agent_submission', {
    success,
    agent_name,
  });
};
