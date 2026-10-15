-- Team plan: organizations and members. Generated from coworker/store.py:ddl("mysql").
-- The coworker store also creates these on first use.
CREATE TABLE IF NOT EXISTS cw_orgs (id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        domain VARCHAR(255) NOT NULL DEFAULT '',
        owner_user_id INT NOT NULL,
        policies MEDIUMTEXT,
        created_at VARCHAR(40) NOT NULL);
CREATE TABLE IF NOT EXISTS cw_org_members (id INT AUTO_INCREMENT PRIMARY KEY,
        org_id INT NOT NULL,
        user_id INT,
        email VARCHAR(255) NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'member',
        status VARCHAR(20) NOT NULL DEFAULT 'invited',
        invited_by INT,
        invited_at VARCHAR(40),
        joined_at VARCHAR(40),
        UNIQUE (org_id, email));
CREATE INDEX idx_cw_org_members_user ON cw_org_members (user_id, status);
