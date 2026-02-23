"""Add phone_number and platform_order_status to order_import_staging

Adds two columns to order_import.order_import_staging:
- phone_number: shipping contact phone (from Shopee Phone Number / Lazada shippingPhone)
- platform_order_status: platform's own order status distinct from manually entered manual_status
  (from Shopee Order Status / Lazada status col 66)

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-02-21 09:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "order_import_staging",
        sa.Column("phone_number", sa.String(50), nullable=True),
        schema="order_import",
    )
    op.add_column(
        "order_import_staging",
        sa.Column("platform_order_status", sa.String(50), nullable=True),
        schema="order_import",
    )


def downgrade() -> None:
    op.drop_column("order_import_staging", "platform_order_status", schema="order_import")
    op.drop_column("order_import_staging", "phone_number", schema="order_import")
