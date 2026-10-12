"""add status to orders

Revision ID: a1b2c3d4e5f6
Revises: 9f8e7d6c5b4a
Create Date: 2026-04-02 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "9f8e7d6c5b4a"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("orders", "legacy_code")
    op.add_column("orders", sa.Column("status", sa.String(length=32), nullable=False))
    op.create_index("ix_orders_status", "orders", ["status"])


def downgrade():
    pass
