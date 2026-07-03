"""initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use SQLite compatible schema generation
    op.create_table(
        "orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_number", sa.String(32), nullable=False, unique=True),
        sa.Column("locale", sa.String(8), nullable=False, server_default="ar"),
        sa.Column("customer_name", sa.String(256), nullable=False),
        sa.Column("phone_raw", sa.String(64), nullable=False),
        sa.Column("phone_e164", sa.String(20), nullable=False),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="new",
        ),
        sa.Column("subtotal_aed", sa.Numeric(10, 2), nullable=False),
        sa.Column("upsell_total_aed", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("total_aed", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="AED"),
        sa.Column("payment_method", sa.String(32), nullable=False, server_default="COD"),
        sa.Column("utm_source", sa.String(256)),
        sa.Column("utm_medium", sa.String(256)),
        sa.Column("utm_campaign", sa.String(256)),
        sa.Column("utm_content", sa.String(256)),
        sa.Column("utm_term", sa.String(256)),
        sa.Column("fbclid", sa.String(512)),
        sa.Column("ttclid", sa.String(512)),
        sa.Column("sc_click_id", sa.String(512)),
        sa.Column("client_ip", sa.String(64)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("landing_page", sa.Text()),
        sa.Column("referrer", sa.Text()),
        sa.Column("purchase_event_id", sa.String(256)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_orders_order_number", "orders", ["order_number"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.String(128), nullable=False),
        sa.Column("product_name_ar", sa.String(512), nullable=False),
        sa.Column("product_name_en", sa.String(512), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("bundle_price_aed", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "unit_context",
            sa.String(32),
            nullable=False,
            server_default="bundle",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "tracking_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_name", sa.String(128), nullable=False),
        sa.Column("event_id", sa.String(256)),
        sa.Column("platform", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text()),
        sa.Column("response_json", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("tracking_events")
    op.drop_table("order_items")
    op.drop_table("orders")
