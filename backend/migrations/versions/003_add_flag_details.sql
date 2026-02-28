-- Add details column to agent_flags for extended flag descriptions
ALTER TABLE agent_flags ADD COLUMN IF NOT EXISTS details TEXT;
