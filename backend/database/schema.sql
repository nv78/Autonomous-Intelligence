DROP TABLE IF EXISTS Subscriptions;
DROP TABLE IF EXISTS StripeInfo;
DROP TABLE IF EXISTS freeTrialsAccessed;
DROP TABLE IF EXISTS prompt_answers;
DROP TABLE IF EXISTS prompts;
DROP TABLE IF EXISTS chunks;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS chats;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS tickers;
DROP TABLE IF EXISTS workflows;
DROP TABLE IF EXISTS apiKeys;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS freeTrialAllowlist;
DROP TABLE IF EXISTS organizations;

CREATE TABLE organizations (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    organization_type VARCHAR(50) NOT NULL,
    website_url VARCHAR(255)
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    email VARCHAR(255) UNIQUE NOT NULL,
    google_id VARCHAR(255),
    person_name VARCHAR(255),
    profile_pic_url VARCHAR(255),
    password_hash VARCHAR(255),
    salt VARCHAR(255),
    session_token VARCHAR(255),
    session_token_expiration TIMESTAMP,
    password_reset_token VARCHAR(255),
    password_reset_token_expiration TIMESTAMP,
    credits INTEGER NOT NULL DEFAULT 0,
    credits_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    chat_gpt_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    num_chatgpt_requests INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE StripeInfo (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    stripe_customer_id VARCHAR(255),
    last_webhook_received TIMESTAMP,
    anchor_date TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE Subscriptions (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    stripe_info_id INTEGER NOT NULL,
    subscription_id VARCHAR(255) NOT NULL,
    start_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP, -- NULL if the subscription is active.
    paid_user INTEGER NOT NULL,
    is_free_trial INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (stripe_info_id) REFERENCES StripeInfo(id)
);

CREATE TABLE freeTrialAllowlist (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    email VARCHAR(255),
    token VARCHAR(255),
    max_non_email_count INTEGER NOT NULL DEFAULT 0,
    token_expiration TIMESTAMP
);

CREATE TABLE freeTrialsAccessed (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    free_trial_allow_list_id INTEGER,
    user_id INTEGER,
    FOREIGN KEY (free_trial_allow_list_id) REFERENCES freeTrialAllowlist(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE chats (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    model_type TINYINT NOT NULL DEFAULT 0,
    chat_name TEXT,
    ticker TEXT,
    associated_task INTEGER NOT NULL,
    custom_model_key TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    message_text TEXT NOT NULL,
    chat_id INTEGER NOT NULL,
    sent_from_user INTEGER NOT NULL,
    relevant_chunks TEXT,
    FOREIGN KEY (chat_id) REFERENCES chats(id)
);

CREATE TABLE workflows (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    workflow_name VARCHAR(255),
    associated_task INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE tickers (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    ticker_name VARCHAR(255) NOT NULL,
    workflow_id INTEGER,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);

CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    workflow_id INTEGER,
    chat_id INTEGER,
    organization_id INTEGER,
    storage_key TEXT NOT NULL,
    document_name VARCHAR(255) NOT NULL,
    document_text LONGTEXT NOT NULL,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id),
    FOREIGN KEY (chat_id) REFERENCES chats(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

CREATE TABLE chunks (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    start_index INTEGER,
    end_index INTEGER,
    document_id INTEGER NOT NULL,
    embedding_vector BLOB,
    page_number INTEGER,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE TABLE prompts (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    workflow_id INTEGER NOT NULL,
    prompt_text TEXT NOT NULL,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);

CREATE TABLE prompt_answers (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    prompt_id INTEGER NOT NULL,
    citation_id INTEGER NOT NULL,
    answer_text TEXT,
    FOREIGN KEY (prompt_id) REFERENCES prompts(id),
    FOREIGN KEY (citation_id) REFERENCES chunks(id)
);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    workflow_id INTEGER NOT NULL,
    report_name VARCHAR(255),
    storage_key TEXT NOT NULL,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);


CREATE TABLE apiKeys (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    api_key VARCHAR(255),
    key_name VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(id)
);


CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE INDEX idx_chats_user_id ON chats(user_id);
CREATE INDEX idx_messages_chat_id ON messages(chat_id);
CREATE INDEX idx_messages_sent_from_user ON messages(sent_from_user);
CREATE INDEX idx_workflows_user_id ON workflows(user_id);
CREATE INDEX idx_api_keys_user_id ON apiKeys(user_id);
CREATE INDEX idx_documents_workflow_id ON documents(workflow_id);
CREATE INDEX idx_documents_chat_id ON documents(chat_id);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_prompts_workflow_id ON prompts(workflow_id);
CREATE INDEX idx_prompt_answers_prompt_id ON prompt_answers(prompt_id);
CREATE INDEX idx_prompt_answers_citation_id ON prompt_answers(citation_id);
CREATE INDEX idx_reports_workflow_id ON reports(workflow_id);
CREATE INDEX idx_tickers_workflow_id ON tickers(workflow_id);
CREATE INDEX idx_organizations_name ON organizations(name);
