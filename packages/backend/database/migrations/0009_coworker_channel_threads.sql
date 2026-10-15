-- Slack bot / text-message conversations mapped to chat threads. Generated from coworker/store.py:ddl("mysql").
-- The coworker store also creates this on first use.
CREATE TABLE IF NOT EXISTS cw_channel_threads (id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        channel VARCHAR(20) NOT NULL,
        thread_key VARCHAR(255) NOT NULL,
        chat_id INT,
        created_at VARCHAR(40) NOT NULL,
        UNIQUE (user_id, channel, thread_key));
