-- SCIM provisioning: each organization's token hash. The coworker store also adds this on first use.
ALTER TABLE cw_orgs ADD COLUMN scim_token_hash VARCHAR(64) NOT NULL DEFAULT '';
