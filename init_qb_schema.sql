CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.qb_invoices (
    id VARCHAR(50) PRIMARY KEY,
    payload JSONB NOT NULL,
    ingested_at_utc TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    extract_window_start_utc TIMESTAMP,
    extract_window_end_utc TIMESTAMP,
    page_number INTEGER,
    page_size INTEGER,
    request_payload JSONB
);

CREATE TABLE IF NOT EXISTS raw.qb_customers (
    id VARCHAR(50) PRIMARY KEY,
    payload JSONB NOT NULL,
    ingested_at_utc TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    extract_window_start_utc TIMESTAMP,
    extract_window_end_utc TIMESTAMP,
    page_number INTEGER,
    page_size INTEGER,
    request_payload JSONB
);

CREATE TABLE IF NOT EXISTS raw.qb_items (
    id VARCHAR(50) PRIMARY KEY,
    payload JSONB NOT NULL,
    ingested_at_utc TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
    extract_window_start_utc TIMESTAMP,
    extract_window_end_utc TIMESTAMP,
    page_number INTEGER,
    page_size INTEGER,
    request_payload JSONB
);

CREATE INDEX IF NOT EXISTS idx_qb_invoices_ingested ON raw.qb_invoices(ingested_at_utc);
CREATE INDEX IF NOT EXISTS idx_qb_customers_ingested ON raw.qb_customers(ingested_at_utc);
CREATE INDEX IF NOT EXISTS idx_qb_items_ingested ON raw.qb_items(ingested_at_utc);
