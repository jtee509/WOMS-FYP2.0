"""
WOMS Order Import Module Models

Dedicated schema for Lazada/Shopee order uploads with:
- OrderImportRaw: Original copies of every Excel row (JSONB), immutable
- OrderImportStaging: Normalized view for processing, links to raw via raw_import_id

Both tables include seller_id to record which seller's orders each row belongs to.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB


# =============================================================================
# Order Import Raw (Original Copies)
# =============================================================================

class OrderImportRaw(SQLModel, table=True):
    """
    Original copies of every Excel row. No transformation. Immutable record.

    Stores complete raw data as JSONB to preserve exact structure regardless of
    platform column changes (Lazada 79 cols, Shopee 61 cols).
    """
    __tablename__ = "order_import_raw"
    __table_args__ = {"schema": "order_import"}

    id: Optional[int] = Field(default=None, primary_key=True)
    seller_id: int = Field(foreign_key="seller.seller_id", index=True)
    platform_source: str = Field(max_length=50, index=True)
    import_batch_id: Optional[str] = Field(default=None, max_length=100, index=True)
    import_filename: Optional[str] = Field(default=None, max_length=500)
    excel_row_number: Optional[int] = Field(default=None)
    raw_row_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
    imported_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    seller: Optional["Seller"] = Relationship()
    staging_rows: List["OrderImportStaging"] = Relationship(
        back_populates="raw_import",
        sa_relationship_kwargs={
            "foreign_keys": "[OrderImportStaging.raw_import_id]",
            "primaryjoin": "OrderImportRaw.id == OrderImportStaging.raw_import_id",
        },
    )


# =============================================================================
# Order Import Staging (Normalized for Processing)
# =============================================================================

class OrderImportStaging(SQLModel, table=True):
    """
    Parsed/normalized view for mapping to orders and order_details.
    Links back to original via raw_import_id.
    """
    __tablename__ = "order_import_staging"
    __table_args__ = {"schema": "order_import"}

    id: Optional[int] = Field(default=None, primary_key=True)
    seller_id: int = Field(foreign_key="seller.seller_id", index=True)
    platform_source: str = Field(max_length=50, index=True)
    platform_order_id: Optional[str] = Field(default=None, max_length=100, index=True)
    order_date: Optional[datetime] = Field(default=None)
    recipient_name: Optional[str] = Field(default=None, max_length=200)
    shipping_address: Optional[str] = Field(default=None, sa_column=Column(Text))
    shipping_postcode: Optional[str] = Field(default=None, max_length=20)
    shipping_state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    platform_sku: Optional[str] = Field(default=None, max_length=200)
    sku_name: Optional[str] = Field(default=None, max_length=500)
    variation_name: Optional[str] = Field(default=None, max_length=200)
    quantity: Optional[int] = Field(default=None)
    unit_price: Optional[Decimal] = Field(default=None)
    paid_amount: Optional[Decimal] = Field(default=None)
    shipping_fee: Optional[Decimal] = Field(default=None)
    discount: Optional[Decimal] = Field(default=None)
    courier_type: Optional[str] = Field(default=None, max_length=100)
    tracking_number: Optional[str] = Field(default=None, max_length=200)
    phone_number: Optional[str] = Field(default=None, max_length=50)
    platform_order_status: Optional[str] = Field(default=None, max_length=50)
    manual_status: Optional[str] = Field(default=None, max_length=50)
    manual_driver: Optional[str] = Field(default=None, max_length=200)
    manual_date: Optional[date] = Field(default=None)
    manual_note: Optional[str] = Field(default=None, sa_column=Column(Text))
    raw_row_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
    )
    raw_import_id: Optional[int] = Field(default=None, index=True)
    normalized_order_id: Optional[int] = Field(
        default=None,
        foreign_key="orders.order_id",
        index=True,
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = Field(default=None)

    # Relationships
    seller: Optional["Seller"] = Relationship()
    raw_import: Optional[OrderImportRaw] = Relationship(
        back_populates="staging_rows",
        sa_relationship_kwargs={
            "foreign_keys": "[OrderImportStaging.raw_import_id]",
            "primaryjoin": "OrderImportStaging.raw_import_id == OrderImportRaw.id",
        },
    )


# Forward reference for Seller
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.orders import Seller
