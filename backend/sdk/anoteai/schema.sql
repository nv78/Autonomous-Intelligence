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
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS freeTrialAllowlist;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_token TEXT,
    session_token_expiration TEXT,
    password_reset_token TEXT,
    password_reset_token_expiration TEXT,
    credits INTEGER NOT NULL DEFAULT 0,
    credits_updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    chat_gpt_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    num_chatgpt_requests INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE StripeInfo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stripe_customer_id TEXT,
    last_webhook_received TEXT,
    anchor_date TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE Subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stripe_info_id INTEGER NOT NULL,
    subscription_id TEXT NOT NULL,
    start_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_date TEXT, -- NULL if the subscription is active.
    paid_user INTEGER NOT NULL,
    is_free_trial INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (stripe_info_id) REFERENCES StripeInfo(id)
);

CREATE TABLE freeTrialAllowlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    email TEXT,
    token TEXT,
    max_non_email_count INTEGER NOT NULL DEFAULT 0,
    token_expiration TEXT
);

CREATE TABLE freeTrialsAccessed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    free_trial_allow_list_id INTEGER,
    user_id INTEGER,
    FOREIGN KEY (free_trial_allow_list_id) REFERENCES freeTrialAllowlist(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER NOT NULL,
    model_type INTEGER NOT NULL DEFAULT 0,
    chat_name TEXT,
    ticker TEXT,
    associated_task INTEGER NOT NULL,
    custom_model_key TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    message_text TEXT NOT NULL,
    chat_id INTEGER NOT NULL,
    sent_from_user INTEGER NOT NULL,
    relevant_chunks TEXT,
    FOREIGN KEY (chat_id) REFERENCES chats(id)
);

CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    chat_id INTEGER,
    storage_key TEXT NOT NULL,
    document_name TEXT NOT NULL,
    document_text TEXT NOT NULL,
    FOREIGN KEY (chat_id) REFERENCES chats(id)
);

CREATE TABLE chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_index INTEGER,
    end_index INTEGER,
    document_id INTEGER NOT NULL,
    embedding_vector BLOB, -- Assuming you store binary data here
    page_number INTEGER,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE INDEX idx_chats_user_id ON chats(user_id);
CREATE INDEX idx_messages_chat_id ON messages(chat_id);
CREATE INDEX idx_messages_sent_from_user ON messages(sent_from_user);
CREATE INDEX idx_documents_chat_id ON documents(chat_id);
CREATE INDEX idx_chunks_document_id ON chunks(document_id);
