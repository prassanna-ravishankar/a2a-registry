-- Durable record of admin moderation decisions. Written in the same statement
-- as the decision itself (AgentRepository.decide_review), so a decision can
-- never land without its record.
CREATE TABLE admin_actions (
    id BIGSERIAL PRIMARY KEY,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    action TEXT NOT NULL CHECK (action IN ('approve', 'reject')),
    previous_status TEXT,
    card_sha256 TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX admin_actions_agent_idx ON admin_actions (agent_id, created_at DESC);
