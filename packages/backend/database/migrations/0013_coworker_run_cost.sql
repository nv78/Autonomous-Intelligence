-- Per-run LLM usage for scheduled tasks. The coworker store also adds these on first use.
ALTER TABLE cw_runs ADD COLUMN tokens INT NOT NULL DEFAULT 0;
ALTER TABLE cw_runs ADD COLUMN cost_micros INT;
