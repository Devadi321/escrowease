-- EscrowEase schema (SQLite)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS deals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    brief           TEXT NOT NULL,
    amount          REAL NOT NULL CHECK (amount > 0),
    currency        TEXT NOT NULL DEFAULT 'USD',
    client_email    TEXT NOT NULL,
    freelancer_email TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'DRAFT'
                    CHECK (status IN ('DRAFT','FUNDED','DELIVERED','APPROVED',
                                      'CHANGES_REQUESTED','RELEASED','REFUNDED')),
    paypal_order_id TEXT,
    paypal_auth_id  TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS deliverables (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id     INTEGER NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    link        TEXT,
    submitted_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS verdicts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id     INTEGER NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    decision    TEXT NOT NULL CHECK (decision IN ('APPROVE','REQUEST_CHANGES')),
    confidence  INTEGER NOT NULL CHECK (confidence BETWEEN 0 AND 100),
    reasons     TEXT NOT NULL,            -- JSON array of strings
    source      TEXT NOT NULL DEFAULT 'pollinations',
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_deliverables_deal ON deliverables(deal_id);
CREATE INDEX IF NOT EXISTS idx_verdicts_deal ON verdicts(deal_id);
