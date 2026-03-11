"""add soft-delete (deleted_at) to reference lookup tables

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-03-06 12:00:00.000000

WHY:
    The four reference lookup tables (item_type, category, brand, base_uom)
    previously used hard-delete, which permanently removed rows from the
    database.  This violates the project's "soft delete only" ground rule
    and makes recovery impossible.

    Adding a nullable `deleted_at` column to each table enables soft-delete:
    - DELETE endpoint sets `deleted_at = now()` instead of removing the row
    - List queries filter WHERE deleted_at IS NULL
    - A restore endpoint can clear `deleted_at` to recover the record

    Partial indexes on the PK WHERE deleted_at IS NULL ensure that the
    hot-path "list all live records" query remains fast.
"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = 'f1a2b3c4d5e6'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None

# Tables to receive the deleted_at column and their PK column names.
_TABLES = {
    "item_type": "item_type_id",
    "category": "category_id",
    "brand": "brand_id",
    "base_uom": "uom_id",
}


def upgrade() -> None:
    for table, pk_col in _TABLES.items():
        # 1. Add deleted_at column (nullable — NULL means live)
        op.add_column(
            table,
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
        )
        # 2. Partial index: fast lookup for live (non-deleted) rows
        op.create_index(
            f"idx_{table}_not_deleted",
            table,
            [pk_col],
            postgresql_where=sa.text("deleted_at IS NULL"),
        )


def downgrade() -> None:
    for table, pk_col in _TABLES.items():
        op.drop_index(f"idx_{table}_not_deleted", table_name=table)
        op.drop_column(table, "deleted_at")
