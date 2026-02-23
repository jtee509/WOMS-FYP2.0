"""Create order_import schema and tables for Lazada/Shopee order uploads

Creates dedicated schema for order import with:
- order_import_raw: Original copies of every Excel row (JSONB), with seller_id
- order_import_staging: Normalized view for processing, links to raw via raw_import_id

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a7
Create Date: 2026-02-20 16:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create order_import schema
    op.execute("CREATE SCHEMA IF NOT EXISTS order_import")

    # order_import_raw: Original copies - immutable record of what was uploaded
    op.create_table(
        "order_import_raw",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("platform_source", sa.String(50), nullable=False),
        sa.Column("import_batch_id", sa.String(100), nullable=True),
        sa.Column("import_filename", sa.String(500), nullable=True),
        sa.Column("excel_row_number", sa.Integer(), nullable=True),
        sa.Column("raw_row_data", JSONB(), nullable=False),
        sa.Column("imported_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["seller_id"], ["seller.seller_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        schema="order_import",
    )
    op.create_index(
        "ix_order_import_raw_seller_id",
        "order_import_raw",
        ["seller_id"],
        schema="order_import",
    )
    op.create_index(
        "ix_order_import_raw_platform_source",
        "order_import_raw",
        ["platform_source"],
        schema="order_import",
    )
    op.create_index(
        "ix_order_import_raw_import_batch_id",
        "order_import_raw",
        ["import_batch_id"],
        schema="order_import",
    )
    op.create_index(
        "ix_order_import_raw_imported_at",
        "order_import_raw",
        ["imported_at"],
        schema="order_import",
    )

    # order_import_staging: Normalized for processing, links to raw
    op.create_table(
        "order_import_staging",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("platform_source", sa.String(50), nullable=False),
        sa.Column("platform_order_id", sa.String(100), nullable=True),
        sa.Column("order_date", sa.DateTime(), nullable=True),
        sa.Column("recipient_name", sa.String(200), nullable=True),
        sa.Column("shipping_address", sa.Text(), nullable=True),
        sa.Column("shipping_postcode", sa.String(20), nullable=True),
        sa.Column("shipping_state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("platform_sku", sa.String(200), nullable=True),
        sa.Column("sku_name", sa.String(500), nullable=True),
        sa.Column("variation_name", sa.String(200), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("paid_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("shipping_fee", sa.Numeric(12, 2), nullable=True),
        sa.Column("discount", sa.Numeric(12, 2), nullable=True),
        sa.Column("courier_type", sa.String(100), nullable=True),
        sa.Column("tracking_number", sa.String(200), nullable=True),
        sa.Column("manual_status", sa.String(50), nullable=True),
        sa.Column("manual_driver", sa.String(200), nullable=True),
        sa.Column("manual_date", sa.Date(), nullable=True),
        sa.Column("manual_note", sa.Text(), nullable=True),
        sa.Column("raw_row_data", JSONB(), nullable=True),
        sa.Column("raw_import_id", sa.BigInteger(), nullable=True),
        sa.Column("normalized_order_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["seller_id"], ["seller.seller_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["normalized_order_id"],
            ["orders.order_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="order_import",
    )
    op.create_index(
        "ix_order_import_staging_seller_id",
        "order_import_staging",
        ["seller_id"],
        schema="order_import",
    )
    op.create_index(
        "ix_order_import_staging_platform_source",
        "order_import_staging",
        ["platform_source"],
        schema="order_import",
    )
    op.create_index(
        "ix_order_import_staging_platform_order_id",
        "order_import_staging",
        ["platform_order_id"],
        schema="order_import",
    )
    op.create_index(
        "ix_order_import_staging_raw_import_id",
        "order_import_staging",
        ["raw_import_id"],
        schema="order_import",
    )
    op.create_index(
        "ix_order_import_staging_normalized_order_id",
        "order_import_staging",
        ["normalized_order_id"],
        schema="order_import",
    )

    # Add FK to order_import_raw (same schema)
    op.create_foreign_key(
        "fk_order_import_staging_raw_import_id",
        "order_import_staging",
        "order_import_raw",
        ["raw_import_id"],
        ["id"],
        source_schema="order_import",
        referent_schema="order_import",
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_table("order_import_staging", schema="order_import")
    op.drop_table("order_import_raw", schema="order_import")
    op.execute("DROP SCHEMA IF EXISTS order_import")
