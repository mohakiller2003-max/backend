"""add cod_lead_id to orders

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("cod_lead_id", sa.String(64), nullable=True))
    op.create_index("ix_orders_cod_lead_id", "orders", ["cod_lead_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_cod_lead_id", table_name="orders")
    op.drop_column("orders", "cod_lead_id")
