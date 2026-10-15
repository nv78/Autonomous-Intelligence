-- Autonomous operations: run timings, retries, and worker heartbeats. Generated from coworker/store.py.
-- The coworker store also applies these on first use (and skips columns that already exist).
ALTER TABLE cw_runs ADD COLUMN started_at VARCHAR(40);
ALTER TABLE cw_runs ADD COLUMN finished_at VARCHAR(40);
ALTER TABLE cw_runs ADD COLUMN attempts INT NOT NULL DEFAULT 1;
ALTER TABLE cw_runs ADD COLUMN error MEDIUMTEXT;
CREATE TABLE IF NOT EXISTS cw_worker_heartbeats (id INT AUTO_INCREMENT PRIMARY KEY,
        worker VARCHAR(120) NOT NULL UNIQUE,
        started_at VARCHAR(40) NOT NULL,
        last_tick_at VARCHAR(40) NOT NULL,
        tick_ms INT NOT NULL DEFAULT 0,
        users INT NOT NULL DEFAULT 0,
        errors INT NOT NULL DEFAULT 0);
