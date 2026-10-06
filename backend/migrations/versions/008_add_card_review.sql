-- Jev (TypeSafe) Agent Card classification and the admin review queue.
-- review_status:
--   NULL      never flagged
--   unscored  Jev could not classify the card; hidden until the worker scores it
--   pending   flagged new or changed card; hidden until an admin decides
--   flagged   flagged card that was already published; stays visible until an admin decides
--   approved  an admin approved this card content (review_approved_sha256)
--   rejected  an admin rejected it; stays hidden
ALTER TABLE agents ADD COLUMN jev_score REAL;
ALTER TABLE agents ADD COLUMN jev_signals JSONB;
ALTER TABLE agents ADD COLUMN jev_model TEXT;
ALTER TABLE agents ADD COLUMN jev_card_sha256 TEXT;
ALTER TABLE agents ADD COLUMN jev_checked_at TIMESTAMPTZ;
ALTER TABLE agents ADD COLUMN review_status TEXT;
ALTER TABLE agents ADD COLUMN review_approved_sha256 TEXT;

ALTER TABLE agents ADD CONSTRAINT agents_review_status_check
    CHECK (review_status IS NULL OR review_status IN ('unscored', 'pending', 'flagged', 'approved', 'rejected'));

CREATE INDEX idx_agents_review_status ON agents (review_status) WHERE review_status IS NOT NULL;
