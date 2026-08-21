CREATE TYPE expense_category AS ENUM (
    'Moradia',
    'Utilidades',
    'Alimentacao',
    'Transporte',
    'Assinaturas',
    'Compras'
);

CREATE TABLE transactions (
    id BIGSERIAL PRIMARY KEY,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0 AND amount < 100000),
    category expense_category NOT NULL,
    sub_category VARCHAR(100) NOT NULL,
    description VARCHAR(300) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE conversation_history (
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    role VARCHAR(9) NOT NULL CHECK (role IN ('user', 'model')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_conversation_history_chat_id_created_at
    ON conversation_history (chat_id, created_at DESC);
