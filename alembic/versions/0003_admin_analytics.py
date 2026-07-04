"""admin analytics schema

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("country_code", sa.String(8), nullable=True))
    op.add_column(
        "orders",
        sa.Column("is_uae_ip", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "analytics_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("page_path", sa.String(512)),
        sa.Column("product_id", sa.String(128)),
        sa.Column("locale", sa.String(8)),
        sa.Column("client_ip", sa.String(64)),
        sa.Column("country_code", sa.String(8)),
        sa.Column("is_uae_ip", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("utm_source", sa.String(256)),
        sa.Column("utm_medium", sa.String(256)),
        sa.Column("utm_campaign", sa.String(256)),
        sa.Column("referrer", sa.Text()),
        sa.Column("user_agent", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_analytics_events_event_type", "analytics_events", ["event_type"])
    op.create_index("ix_analytics_events_session_id", "analytics_events", ["session_id"])
    op.create_index("ix_analytics_events_is_uae_ip", "analytics_events", ["is_uae_ip"])
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"])
    op.create_index("ix_orders_is_uae_ip", "orders", ["is_uae_ip"])


def downgrade() -> None:
    op.drop_index("ix_orders_is_uae_ip", table_name="orders")
    op.drop_index("ix_analytics_events_created_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_is_uae_ip", table_name="analytics_events")
    op.drop_index("ix_analytics_events_session_id", table_name="analytics_events")
    op.drop_index("ix_analytics_events_event_type", table_name="analytics_events")
    op.drop_table("analytics_events")
    op.drop_column("orders", "is_uae_ip")
    op.drop_column("orders", "country_code")
