-- Jev-assigned category (backend/app/categories.py), written with each classification.
-- Slugs are validated in the application so the category list can change without a migration.
ALTER TABLE agents ADD COLUMN category TEXT;
ALTER TABLE agents ADD COLUMN category_secondary TEXT;
ALTER TABLE agents ADD COLUMN category_confidence REAL;

CREATE INDEX idx_agents_category ON agents (category) WHERE category IS NOT NULL;
