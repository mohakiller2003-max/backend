-- Skinouva admin dashboard migration (0003)
-- Run on PostgreSQL if not using Alembic auto-migrate

ALTER TABLE orders ADD COLUMN IF NOT EXISTS country_code VARCHAR(8);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_uae_ip BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS analytics_events (
    id VARCHAR(36) PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    page_path VARCHAR(512),
    product_id VARCHAR(128),
    locale VARCHAR(8),
    client_ip VARCHAR(64),
    country_code VARCHAR(8),
    is_uae_ip BOOLEAN NOT NULL DEFAULT FALSE,
    utm_source VARCHAR(256),
    utm_medium VARCHAR(256),
    utm_campaign VARCHAR(256),
    referrer TEXT,
    user_agent TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_analytics_events_event_type ON analytics_events (event_type);
CREATE INDEX IF NOT EXISTS ix_analytics_events_session_id ON analytics_events (session_id);
CREATE INDEX IF NOT EXISTS ix_analytics_events_is_uae_ip ON analytics_events (is_uae_ip);
CREATE INDEX IF NOT EXISTS ix_analytics_events_created_at ON analytics_events (created_at);
CREATE INDEX IF NOT EXISTS ix_orders_is_uae_ip ON orders (is_uae_ip);
