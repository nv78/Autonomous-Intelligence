-- Background sync jobs and owner notifications. Generated from coworker/store.py:ddl("mysql").
-- The coworker store also creates these on first use.
CREATE TABLE IF NOT EXISTS cw_sync_jobs (id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'queued',
        phase VARCHAR(20) NOT NULL DEFAULT 'queued',
        rebuild INT NOT NULL DEFAULT 0,
        counts MEDIUMTEXT,
        error MEDIUMTEXT,
        requested_at VARCHAR(40) NOT NULL,
        started_at VARCHAR(40),
        finished_at VARCHAR(40));
CREATE TABLE IF NOT EXISTS cw_notifications (id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        kind VARCHAR(30) NOT NULL,
        slot VARCHAR(40) NOT NULL,
        channel VARCHAR(20) NOT NULL DEFAULT '',
        subject VARCHAR(500) NOT NULL DEFAULT '',
        item_count INT NOT NULL DEFAULT 0,
        sent_at VARCHAR(40) NOT NULL,
        UNIQUE (user_id, kind, slot));
CREATE INDEX idx_cw_sync_jobs_user ON cw_sync_jobs (user_id, status);
