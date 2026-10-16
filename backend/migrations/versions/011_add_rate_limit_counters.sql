-- Fixed-window counters for per-client request limits and the Jev spend
-- ceiling, shared by every API replica and the worker. window_end is epoch
-- seconds; the worker deletes ended windows each cycle.
CREATE TABLE rate_limit_counters (
    scope TEXT NOT NULL,
    window_end BIGINT NOT NULL,
    used INTEGER NOT NULL CHECK (used >= 0),
    PRIMARY KEY (scope, window_end)
);

CREATE INDEX rate_limit_counters_window_end_idx ON rate_limit_counters (window_end);
