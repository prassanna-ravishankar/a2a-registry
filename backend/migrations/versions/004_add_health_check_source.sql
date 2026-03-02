ALTER TABLE health_checks ADD COLUMN source VARCHAR(10) NOT NULL DEFAULT 'worker';
CREATE INDEX idx_health_checks_source ON health_checks(agent_id, source, checked_at DESC);
