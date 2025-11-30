import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Initialize PostHog (with graceful degradation if blocked by ad blocker)
try {
  const posthogModule = await import('posthog-js');
  const posthog = posthogModule.default;

  if (import.meta.env.VITE_POSTHOG_KEY) {
    posthog.init(import.meta.env.VITE_POSTHOG_KEY, {
      api_host: import.meta.env.VITE_POSTHOG_HOST || 'https://us.posthog.com',
      autocapture: true,
      capture_pageview: true,
      capture_pageleave: true,
    });

    // Make posthog available globally for analytics.js
    window.posthog = posthog;
  }
} catch (e) {
  console.info('Analytics unavailable (likely blocked) - app will continue without tracking');
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);