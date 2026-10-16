-- Telegram chats linked to coworkers. Generated from coworker/store.py:ddl("mysql").
-- The coworker store also creates this on first use.
CREATE TABLE IF NOT EXISTS cw_telegram (id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        chat_id VARCHAR(40) NOT NULL DEFAULT '',
        username VARCHAR(255) NOT NULL DEFAULT '',
        link_hash VARCHAR(64) NOT NULL DEFAULT '',
        link_expires VARCHAR(40),
        linked_at VARCHAR(40),
        prefs MEDIUMTEXT,
        created_at VARCHAR(40) NOT NULL);
CREATE INDEX idx_cw_telegram_chat ON cw_telegram (chat_id);
CREATE INDEX idx_cw_telegram_link ON cw_telegram (link_hash);
