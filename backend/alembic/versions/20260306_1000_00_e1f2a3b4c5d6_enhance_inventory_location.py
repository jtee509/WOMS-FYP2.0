"""enhance inventory_location: is_active, sort_order, display_code, composite unique

Revision ID: e1f2a3b4c5d6
Revises: c4d5e6f7a8b9
Create Date: 2026-03-06 10:00:00.000000

WHY:
    The inventory_location table lacked several columns needed for production
    warehouse operations:

    1. is_active (BOOLEAN, DEFAULT TRUE)
       Locations can be temporarily decommissioned (e.g. during maintenance or
       re-racking) without soft-deleting them.  `deleted_at` is for permanent
       removal; `is_active` is for operational on/off toggling.

    2. sort_order (INTEGER, nullable)
       Warehouse managers need to define a pick-path ordering for locations.
       Alphabetical sorting by section/zone/aisle does not reflect the
       physical walking path in every warehouse layout.

    3. display_code (VARCHAR 255)
       The existing Python property `full_location_code` only works in-memory.
       A persisted column enables SQL-level WHERE/ORDER BY on the human-
       readable code (e.g. "A1-Z1-A01-R5-B12").  Populated automatically by
       a BEFORE INSERT trigger defined in triggers.py.

    4. Composite UNIQUE index on (warehouse_id, section, zone, aisle, rack, bin)
       Prevents two location records from describing the same physical address
       inside one warehouse.  Uses COALESCE to treat NULLs as empty strings
       so that partial addresses still participate in the constraint.

    5. Partial index on is_active (WHERE is_active = TRUE)
       Optimises the hot-path query "give me all active locations in warehouse X".

    6. BEFORE INSERT trigger: generate_location_display_code
       Concatenates non-null hierarchy segments (section, zone, aisle, rack, bin)
       with a hyphen separator and writes the result into display_code.
       Defined in triggers.py; this migration creates the trigger + function
       so that existing databases receive it immediately.
"""

from alembic import op
import sqlalchemy as sa


# Revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'cc0305drop01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Add new columns
    # ------------------------------------------------------------------
    op.add_column(
        'inventory_location',
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
    )
    op.add_column(
        'inventory_location',
        sa.Column('sort_order', sa.Integer(), nullable=True),
    )
    op.add_column(
        'inventory_location',
        sa.Column('display_code', sa.String(255), nullable=True),
    )

    # ------------------------------------------------------------------
    # 2. Composite UNIQUE index — prevents duplicate physical addresses.
    #    COALESCE wraps each nullable column so that (NULL, NULL, NULL,
    #    NULL, NULL) in warehouse 1 cannot appear twice.
    # ------------------------------------------------------------------
    op.execute(sa.text("""
        CREATE UNIQUE INDEX uq_location_address
        ON inventory_location (
            warehouse_id,
            COALESCE(section, ''),
            COALESCE(zone, ''),
            COALESCE(aisle, ''),
            COALESCE(rack, ''),
            COALESCE(bin, '')
        )
    """))

    # ------------------------------------------------------------------
    # 3. Partial index — active locations only (hot-path optimisation)
    # ------------------------------------------------------------------
    op.create_index(
        'idx_inventory_location_active',
        'inventory_location',
        ['warehouse_id', 'is_active'],
        postgresql_where=sa.text('is_active = TRUE'),
    )

    # ------------------------------------------------------------------
    # 4. Trigger function + trigger — auto-generate display_code
    # ------------------------------------------------------------------
    op.execute(sa.text("""
        CREATE OR REPLACE FUNCTION generate_location_display_code()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.display_code = CONCAT_WS(
                '-',
                NULLIF(NEW.section, ''),
                NULLIF(NEW.zone, ''),
                NULLIF(NEW.aisle, ''),
                NULLIF(NEW.rack, ''),
                NULLIF(NEW.bin, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """))

    op.execute(sa.text(
        "DROP TRIGGER IF EXISTS trg_generate_display_code ON inventory_location"
    ))
    op.execute(sa.text("""
        CREATE TRIGGER trg_generate_display_code
            BEFORE INSERT ON inventory_location
            FOR EACH ROW
            EXECUTE FUNCTION generate_location_display_code()
    """))

    # ------------------------------------------------------------------
    # 5. Backfill display_code for existing rows
    # ------------------------------------------------------------------
    op.execute(sa.text("""
        UPDATE inventory_location
        SET display_code = CONCAT_WS(
            '-',
            NULLIF(section, ''),
            NULLIF(zone, ''),
            NULLIF(aisle, ''),
            NULLIF(rack, ''),
            NULLIF(bin, '')
        )
    """))


def downgrade() -> None:
    # Drop trigger + function
    op.execute(sa.text(
        "DROP TRIGGER IF EXISTS trg_generate_display_code ON inventory_location"
    ))
    op.execute(sa.text(
        "DROP FUNCTION IF EXISTS generate_location_display_code()"
    ))

    # Drop indexes
    op.drop_index('idx_inventory_location_active', table_name='inventory_location')
    op.execute(sa.text("DROP INDEX IF EXISTS uq_location_address"))

    # Drop columns
    op.drop_column('inventory_location', 'display_code')
    op.drop_column('inventory_location', 'sort_order')
    op.drop_column('inventory_location', 'is_active')
