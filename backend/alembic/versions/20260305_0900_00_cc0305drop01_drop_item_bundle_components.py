"""drop item_bundle_components table

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-03-05 09:00:00.000000

WHY:
    The Bundle feature (BOM / Bill-of-Materials) has been removed from WOMS.
    Bundles added complexity without sufficient business value at this stage.
    The `item_bundle_components` table stored BOM rows — which physical items
    are deducted when a bundle is sold. Dropping it removes all listing
    component data from the database.

    Items that previously had item_type = "Bundle" remain as regular Item
    rows and will now appear in the standard Items list. The "Bundle" item
    type row in `item_types` is NOT removed by this migration — it can be
    manually cleaned up via the Settings > Item Types UI if desired.
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = 'cc0305drop01'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table('item_bundle_components')


def downgrade() -> None:
    # Re-creating the table on downgrade — column definitions match the
    # original ItemBundleComponent model exactly.
    import sqlalchemy as sa
    op.create_table(
        'item_bundle_components',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bundle_item_id', sa.Integer(), nullable=False),
        sa.Column('component_item_id', sa.Integer(), nullable=False),
        sa.Column('quantity_per_bundle', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['bundle_item_id'], ['items.item_id'], ),
        sa.ForeignKeyConstraint(['component_item_id'], ['items.item_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bundle_item_id', 'component_item_id',
                            name='uq_bundle_component'),
    )
