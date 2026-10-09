-- INPUT: the endpoint rejected the plain-text probe as invalid params because it
-- expects structured input; reachable but not exercisable by the probe (#184).
-- BLOCKED: the card's endpoint resolves to a non-public address (SSRF guard).
ALTER TABLE agents DROP CONSTRAINT agents_task_conformance_category_check;
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
        'INPUT',
        'BLOCKED',
        'INTERNAL',
        'TIMEOUT',
        'OTHER'
    ));
