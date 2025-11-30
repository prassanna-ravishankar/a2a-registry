-- Initial database schema for A2A Registry

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Agents table
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- A2A Protocol fields
    protocol_version VARCHAR(20) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    author VARCHAR(255) NOT NULL,
    well_known_uri TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    version VARCHAR(50) NOT NULL,

    -- JSONB fields for complex structures
    provider JSONB,
    documentation_url TEXT,
    capabilities JSONB NOT NULL,
    default_input_modes JSONB NOT NULL,
    default_output_modes JSONB NOT NULL,
    skills JSONB NOT NULL,

    -- Registry metadata
    hidden BOOLEAN DEFAULT FALSE,
    flag_count INTEGER DEFAULT 0
);

-- Indexes for agents
CREATE INDEX idx_agents_author ON agents(author);
CREATE INDEX idx_agents_created_at ON agents(created_at DESC);
CREATE INDEX idx_agents_skills ON agents USING gin(skills);
CREATE INDEX idx_agents_capabilities ON agents USING gin(capabilities);
CREATE INDEX idx_agents_hidden ON agents(hidden) WHERE hidden = false;

-- Health checks table
CREATE TABLE health_checks (
    id BIGSERIAL PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    status_code INTEGER,
    response_time_ms INTEGER,
    success BOOLEAN NOT NULL,
    error_message TEXT
);

-- Indexes for health_checks
CREATE INDEX idx_health_checks_agent_time ON health_checks(agent_id, checked_at DESC);
CREATE INDEX idx_health_checks_checked_at ON health_checks(checked_at DESC);
CREATE INDEX idx_health_checks_success ON health_checks(success, checked_at DESC);

-- Agent flags table (community reports)
CREATE TABLE agent_flags (
    id BIGSERIAL PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    flagged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reason TEXT,
    ip_address INET
);

-- Index for agent_flags
CREATE INDEX idx_agent_flags_agent_id ON agent_flags(agent_id);
CREATE INDEX idx_agent_flags_flagged_at ON agent_flags(flagged_at DESC);

-- Trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments for documentation
COMMENT ON TABLE agents IS 'Registry of A2A Protocol agents';
COMMENT ON TABLE health_checks IS 'Health check history for agents';
COMMENT ON TABLE agent_flags IS 'Community flags/reports for problematic agents';

COMMENT ON COLUMN agents.well_known_uri IS 'Agent''s /.well-known/agent.json endpoint';
COMMENT ON COLUMN agents.hidden IS 'Soft delete flag - hides from public listings';
COMMENT ON COLUMN agents.flag_count IS 'Number of community flags received';
COMMENT ON COLUMN health_checks.response_time_ms IS 'Response time in milliseconds';
