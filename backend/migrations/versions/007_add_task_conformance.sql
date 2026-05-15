-- Task conformance: results from periodic A2A message/send probes (smoke_test.py).
-- Separate from `conformance` (card schema validation). NULL = not yet probed.
ALTER TABLE agents ADD COLUMN task_conformance_category TEXT;
ALTER TABLE agents ADD COLUMN task_conformance_passed BOOLEAN;
ALTER TABLE agents ADD COLUMN task_conformance_checked_at TIMESTAMPTZ;
ALTER TABLE agents ADD COLUMN task_conformance_response_ms INTEGER;

-- Restrict category to the smoke_test.py taxonomy so values don't drift.
ALTER TABLE agents ADD CONSTRAINT agents_task_conformance_category_check
    CHECK (task_conformance_category IS NULL OR task_conformance_category IN (
        'WORKING',
        'NO_TRANSPORTS',
        '404', '405', '401', '402', '403', '400',
        'DNS',
        'VERSION',
        'BAD_RESPONSE',
        'BAD_JSON',
        'METHOD',
        'PARSE',
        'AUTH_BACKEND',
        'INTERNAL',
        'TIMEOUT',
        'OTHER'
    ));
