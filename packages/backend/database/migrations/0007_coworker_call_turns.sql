-- Live-call turn buffer (turn-taking across server processes). Generated from coworker/store.py:ddl("mysql").
-- The coworker store also creates it on first use.
CREATE TABLE IF NOT EXISTS cw_turns (id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        meeting_id INT NOT NULL,
        text MEDIUMTEXT,
        status VARCHAR(20) NOT NULL DEFAULT 'new',
        claimed_by INT,
        created_at VARCHAR(40) NOT NULL);
CREATE INDEX idx_cw_turns_meeting ON cw_turns (meeting_id, status);
