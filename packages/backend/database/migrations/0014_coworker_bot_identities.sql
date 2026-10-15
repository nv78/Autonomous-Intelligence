-- Teams / Google Chat: which chat identity is which owner. Generated from coworker/store.py:ddl("mysql").
-- The coworker store also creates this on first use.
CREATE TABLE IF NOT EXISTS cw_bot_identities (id INT AUTO_INCREMENT PRIMARY KEY,
        platform VARCHAR(20) NOT NULL,
        external_id VARCHAR(255) NOT NULL,
        user_id INT NOT NULL,
        tenant VARCHAR(255) NOT NULL DEFAULT '',
        email VARCHAR(255) NOT NULL DEFAULT '',
        conversation MEDIUMTEXT,
        created_at VARCHAR(40) NOT NULL,
        UNIQUE (platform, external_id));
