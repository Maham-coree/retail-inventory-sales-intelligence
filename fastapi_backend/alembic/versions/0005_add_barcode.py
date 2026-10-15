"""Add the missing product barcode column to this workspace's base schema.

Revision ID: 0005_add_barcode
Revises: 0004_db_objects
"""

from alembic import op

revision = "0005_add_barcode"
down_revision = "0004_db_objects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE retail.products ADD COLUMN barcode varchar(50)")
    op.execute("CREATE UNIQUE INDEX uq_products_barcode ON retail.products USING btree(barcode)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS retail.uq_products_barcode")
    op.execute("ALTER TABLE retail.products DROP COLUMN IF EXISTS barcode")
