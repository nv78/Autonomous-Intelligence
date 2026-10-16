-- Email your coworker: each owner's personal coworker address. Generated from coworker/store.py:ddl("mysql").
-- The coworker store also creates this on first use.
CREATE TABLE IF NOT EXISTS cw_inbound_addresses (id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        handle VARCHAR(64) NOT NULL UNIQUE,
        created_at VARCHAR(40) NOT NULL);
