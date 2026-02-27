-- Migration 002: Add A2A spec fields
ALTER TABLE agents
  ADD COLUMN IF NOT EXISTS icon_url TEXT,
  ADD COLUMN IF NOT EXISTS supports_authenticated_extended_card BOOLEAN,
  ADD COLUMN IF NOT EXISTS security_requirements JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS security_schemes JSONB DEFAULT '{}'::jsonb;
