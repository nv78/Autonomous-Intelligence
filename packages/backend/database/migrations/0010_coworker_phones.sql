-- Text your coworker: linked, verified phone numbers. Generated from coworker/store.py:ddl("mysql").
-- The coworker store also creates this on first use.
CREATE TABLE IF NOT EXISTS cw_phones (id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        number VARCHAR(20) NOT NULL,
        verified INT NOT NULL DEFAULT 0,
        code_hash VARCHAR(64) NOT NULL DEFAULT '',
        code_sent_at VARCHAR(40),
        attempts INT NOT NULL DEFAULT 0,
        prefs MEDIUMTEXT,
        created_at VARCHAR(40) NOT NULL);
CREATE INDEX idx_cw_phones_number ON cw_phones (number, verified);
