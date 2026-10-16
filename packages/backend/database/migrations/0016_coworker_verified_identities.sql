-- Verified identities (Google/Microsoft) and session revocation. Generated from coworker/store.py:ddl("mysql").
-- The coworker store also creates these on first use.
CREATE TABLE IF NOT EXISTS cw_verified_identities (id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        provider VARCHAR(20) NOT NULL,
        subject VARCHAR(255) NOT NULL,
        email VARCHAR(255) NOT NULL DEFAULT '',
        managed_domain VARCHAR(255) NOT NULL DEFAULT '',
        tenant VARCHAR(255) NOT NULL DEFAULT '',
        created_at VARCHAR(40) NOT NULL,
        last_seen_at VARCHAR(40),
        UNIQUE (provider, subject));
CREATE INDEX idx_cw_verified_user ON cw_verified_identities (user_id);
CREATE TABLE IF NOT EXISTS cw_auth_epochs (id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL UNIQUE,
        tokens_valid_after VARCHAR(40) NOT NULL);
