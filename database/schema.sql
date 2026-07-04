-- LendIQ logical schema (PostgreSQL DDL).
-- The demo runtime uses Firestore/local-JSON with the same collection names;
-- this DDL is the enterprise-grade relational equivalent (ER source of truth).

CREATE TABLE customer (
    customer_id     VARCHAR(20) PRIMARY KEY,
    name            VARCHAR(120) NOT NULL,
    pan             VARCHAR(10),
    employer        VARCHAR(120),
    consent_id      VARCHAR(64),           -- AA consent artefact
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE account (
    account_id      VARCHAR(20) PRIMARY KEY,
    customer_id     VARCHAR(20) NOT NULL REFERENCES customer,
    fip_name        VARCHAR(80),           -- bank holding the account
    account_type    VARCHAR(20) DEFAULT 'SAVINGS',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE transaction (
    txn_id          VARCHAR(32) PRIMARY KEY,
    account_id      VARCHAR(20) NOT NULL REFERENCES account,
    txn_date        DATE NOT NULL,
    amount          NUMERIC(14,2) NOT NULL,
    txn_type        VARCHAR(6) NOT NULL CHECK (txn_type IN ('CREDIT','DEBIT')),
    mode            VARCHAR(10),           -- UPI/NEFT/ATM/CARD/CASH/ECS
    narration       TEXT,
    balance         NUMERIC(14,2),
    category        VARCHAR(30)            -- SALARY/EMI/RENT/...
);
CREATE INDEX idx_txn_account_date ON transaction (account_id, txn_date);
CREATE INDEX idx_txn_category ON transaction (category);

CREATE TABLE features (
    customer_id     VARCHAR(20) PRIMARY KEY REFERENCES customer,
    feature_json    JSONB NOT NULL,        -- canonical 34-feature vector
    computed_at     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE prediction (
    prediction_id   BIGSERIAL PRIMARY KEY,
    customer_id     VARCHAR(20) NOT NULL REFERENCES customer,
    model_name      VARCHAR(20) NOT NULL,  -- income/intent/risk
    model_version   VARCHAR(40),
    output_json     JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_prediction_customer ON prediction (customer_id, model_name);

CREATE TABLE lead_score (
    customer_id     VARCHAR(20) PRIMARY KEY REFERENCES customer,
    score           NUMERIC(5,2) NOT NULL,
    tier            VARCHAR(5) NOT NULL CHECK (tier IN ('HOT','WARM','COLD')),
    conversion_prob NUMERIC(5,4),
    components      JSONB,
    scored_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE recommendation (
    recommendation_id BIGSERIAL PRIMARY KEY,
    customer_id     VARCHAR(20) NOT NULL REFERENCES customer,
    product         VARCHAR(30) NOT NULL,
    eligible_amount NUMERIC(14,2),
    rate_min        NUMERIC(5,2),
    rate_max        NUMERIC(5,2),
    tenure_months   INT,
    monthly_emi     NUMERIC(12,2),
    reasons         JSONB,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE audit (
    audit_id        BIGSERIAL PRIMARY KEY,
    action          VARCHAR(60) NOT NULL,
    detail          JSONB,
    at              TIMESTAMPTZ DEFAULT now()
);
