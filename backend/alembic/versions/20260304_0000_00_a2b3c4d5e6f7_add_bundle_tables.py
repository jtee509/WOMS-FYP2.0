"""Add item_bundle_components table and reserved_quantity column

Creates the Bill-of-Materials join table for Bundle SKU inventory management.
Adds reserved_quantity to inventory_levels for pessimistic stock reservation.

Revision ID: a2b3c4d5e6f7
Revises: f6a7b8c9d0e1
Create Date: 2026-03-04 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. item_bundle_components — Bill of Materials join table
    op.create_table(
        "item_bundle_components",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "bundle_item_id",
            sa.Integer(),
            sa.ForeignKey("items.item_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "component_item_id",
            sa.Integer(),
            sa.ForeignKey("items.item_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "quantity_per_bundle",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "idx_bundle_components_bundle",
        "item_bundle_components",
        ["bundle_item_id"],
    )
    op.create_index(
        "idx_bundle_components_component",
        "item_bundle_components",
        ["component_item_id"],
    )
    op.create_unique_constraint(
        "uq_bundle_component",
        "item_bundle_components",
        ["bundle_item_id", "component_item_id"],
    )

    # 2. reserved_quantity on inventory_levels
    op.add_column(
        "inventory_levels",
        sa.Column(
            "reserved_quantity",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("inventory_levels", "reserved_quantity")
    op.drop_index("idx_bundle_components_component", table_name="item_bundle_components")
    op.drop_index("idx_bundle_components_bundle", table_name="item_bundle_components")
    op.drop_constraint("uq_bundle_component", "item_bundle_components", type_="unique")
    op.drop_table("item_bundle_components")
