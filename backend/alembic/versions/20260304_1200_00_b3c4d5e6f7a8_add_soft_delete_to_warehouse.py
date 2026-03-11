"""add soft delete to warehouse and inventory_location

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-03-04 12:00:00.000000

WHY:
    Implements soft-delete for the Warehouse and InventoryLocation tables.
    Instead of hard-deleting rows (which would cascade-break inventory levels,
    movements, and alert history), setting `deleted_at` preserves all relational
    history while hiding the record from standard queries.

    Cascade rule: deleting a warehouse also soft-deletes all its locations
    (done in the router via a bulk UPDATE, not a DB-level cascade, so we retain
    control and auditability).

    Two partial indexes are added so standard "not deleted" filters hit the
    smallest possible index structure.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7a8'
down_revision = 'a2b3c4d5e6f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── warehouse ──────────────────────────────────────────────────────────
    op.add_column(
        'warehouse',
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
    )
    op.create_index(
        'idx_warehouse_not_deleted',
        'warehouse',
        ['id'],
        postgresql_where=sa.text('deleted_at IS NULL'),
    )

    # ── inventory_location ─────────────────────────────────────────────────
    op.add_column(
        'inventory_location',
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
    )
    op.create_index(
        'idx_inventory_location_not_deleted',
        'inventory_location',
        ['id'],
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('idx_inventory_location_not_deleted', table_name='inventory_location')
    op.drop_column('inventory_location', 'deleted_at')

    op.drop_index('idx_warehouse_not_deleted', table_name='warehouse')
    op.drop_column('warehouse', 'deleted_at')
