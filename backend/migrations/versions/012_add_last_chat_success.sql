-- Last successful user chat through the registry proxy. Kept on the agent, not
-- as a health_checks row, because uptime and liveness queries count every
-- health_checks row regardless of source. Clears older chat-error notes.
ALTER TABLE agents ADD COLUMN last_chat_success_at TIMESTAMPTZ;
