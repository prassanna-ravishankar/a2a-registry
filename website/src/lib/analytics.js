// Analytics functions with graceful degradation when blocked by ad blockers
// All functions are safe to call even if analytics is blocked

const trackEvent = (eventName, properties = {}) => {
  try {
    // Check if posthog is available globally (set by main.jsx)
    if (typeof window !== 'undefined' && window.posthog && typeof window.posthog.capture === 'function') {
      window.posthog.capture(eventName, properties);
    }
  } catch (e) {
    // Silently fail - analytics should never break the app
  }
};

export const trackAgentView = (agent) => {
  trackEvent('agent_viewed', {
    agent_id: agent?.id,
    agent_name: agent?.name,
    agent_author: agent?.author,
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
