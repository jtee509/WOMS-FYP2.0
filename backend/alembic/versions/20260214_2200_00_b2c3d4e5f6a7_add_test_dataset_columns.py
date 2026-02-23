"""Add test dataset columns (platform address/postcode, seller company_name, items sku_name/product_number)

Adds columns from the test Excel datasets to support full data persistence:
- platform: address, postcode (from test platform.xlsx)
- seller: company_name (from test sellers.xlsx)
- items: sku_name, product_number (from test items.xlsx)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-14 22:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Platform: address and postcode (from test platform.xlsx Address, Postcode columns)
    op.add_column(
        "platform",
        sa.Column("address", sa.String(500), nullable=True),
    )
    op.add_column(
        "platform",
        sa.Column("postcode", sa.String(20), nullable=True),
    )

    # Seller: company_name (from test sellers.xlsx Company Name column)
    op.add_column(
        "seller",
        sa.Column("company_name", sa.String(200), nullable=True),
    )

    # Items: sku_name and product_number (from test items.xlsx SKU Name, No. columns)
    op.add_column(
        "items",
        sa.Column("sku_name", sa.String(500), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column("product_number", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_column("items", "product_number")
    op.drop_column("items", "sku_name")
    op.drop_column("seller", "company_name")
    op.drop_column("platform", "postcode")
    op.drop_column("platform", "address")
