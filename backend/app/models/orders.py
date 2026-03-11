"""
WOMS Orders Module Models

This module contains all order and platform-related models:
- Platform: E-commerce platforms (Shopee, Lazada, etc.)
- Seller: Seller/store accounts on platforms
- PlatformSKU: Platform-specific product listings
- ListingComponent: Links platform listings to items (for bundles/kits)
- CustomerPlatform: Customer data per platform
- PlatformRawImport: Raw platform data storage for Excel/API imports
- Order: Main order entity
- OrderDetail: Order line items with pricing and shipping info
- CancellationReason: Lookup table for cancellation reasons
- OrderCancellation: Tracks order and item-level cancellations

For order operations (returns, exchanges, modifications, price adjustments),
see app.models.order_operations module.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB


# =============================================================================
# Platform & Seller Tables (Translator Module)
# =============================================================================

class Platform(SQLModel, table=True):
    """
    E-commerce platform definitions.
    
    Examples: Shopee, Lazada, TikTok Shop, Shopify, WooCommerce, etc.
    """
    __tablename__ = "platform"
    
    platform_id: Optional[int] = Field(default=None, primary_key=True)
    platform_name: str = Field(max_length=100, unique=True, index=True)
    
    # Address from test dataset (e.g. Showroom physical location)
    address: Optional[str] = Field(default=None, max_length=500)
    postcode: Optional[str] = Field(default=None, max_length=20)
    
    # Optional platform configuration
    api_endpoint: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    is_online: bool = Field(default=True, description="True = online marketplace, False = offline/physical store")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    sellers: List["Seller"] = Relationship(back_populates="platform")
    platform_skus: List["PlatformSKU"] = Relationship(back_populates="platform")
    orders: List["Order"] = Relationship(back_populates="platform")
    customers: List["CustomerPlatform"] = Relationship(back_populates="platform")
    raw_imports: List["PlatformRawImport"] = Relationship(back_populates="platform")


class Seller(SQLModel, table=True):
    """
    Seller/store accounts on platforms.
    
    A seller can have multiple stores across different platforms.
    """
    __tablename__ = "seller"
    __table_args__ = (
        # Partial index — active sellers only (very common filter in routing/lookup)
        Index("idx_sellers_active", "seller_id", "store_name",
              postgresql_where=text("is_active = TRUE")),
    )

    seller_id: Optional[int] = Field(default=None, primary_key=True)
    store_name: str = Field(max_length=200, index=True)
    platform_id: Optional[int] = Field(default=None, foreign_key="platform.platform_id")
    
    # Store identification on platform
    platform_store_id: Optional[str] = Field(default=None, max_length=100)
    
    # Company name from test dataset
    company_name: Optional[str] = Field(default=None, max_length=200)
    
    is_active: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    platform: Optional[Platform] = Relationship(back_populates="sellers")
    platform_skus: List["PlatformSKU"] = Relationship(back_populates="seller")
    orders: List["Order"] = Relationship(back_populates="store")
    raw_imports: List["PlatformRawImport"] = Relationship(back_populates="seller")
    seller_warehouses: List["SellerWarehouse"] = Relationship(back_populates="seller")


# =============================================================================
# Platform Raw Data Import Table
# =============================================================================

class PlatformRawImport(SQLModel, table=True):
    """
    Raw platform data storage for Excel/API imports.
    
    Preserves original data from platform exports (Excel files, API responses)
    for auditing, debugging, and reprocessing purposes.
    
    Features:
    - Stores complete raw data as JSONB
    - Tracks import source and processing status
    - Links to normalized order after processing
    
    Example raw_data for Shopee Excel import:
    {
        "Order ID": "2301234567890",
        "Order Status": "Completed",
        "SKU Reference No.": "SKU001",
        "Variation Name": "Red-XL",
        "Original Price": 50.00,
        ...
    }
    """
    __tablename__ = "platform_raw_imports"
    __table_args__ = (
        # GIN index on raw JSONB — enables platform-specific field queries on raw imports
        Index("idx_raw_import_data_gin", "raw_data",
              postgresql_using="gin",
              postgresql_ops={"raw_data": "jsonb_path_ops"}),
        # Composite: status + platform — processing queue queries by platform
        Index("idx_raw_imports_processing", "status", "platform_id"),
        # Partial: pending imports only — fast lookup for background processor
        Index("idx_raw_imports_pending", "platform_id", "created_at",
              postgresql_where=text("status = 'pending'")),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Platform and seller references
    platform_id: int = Field(foreign_key="platform.platform_id", index=True)
    seller_id: Optional[int] = Field(default=None, foreign_key="seller.seller_id", index=True)
    
    # Import source tracking
    import_source: str = Field(
        max_length=50,
        index=True,
        description="Source type: 'excel', 'api', 'manual'"
    )
    import_filename: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Original filename for Excel imports"
    )
    import_batch_id: Optional[str] = Field(
        default=None,
        max_length=100,
        index=True,
        description="Batch ID for grouping related imports"
    )
    
    # Raw data storage
    raw_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
        description="Complete raw data from platform export"
    )
    
    # Processing status
    status: str = Field(
        default="pending",
        max_length=50,
        index=True,
        description="Processing status: 'pending', 'processed', 'error', 'skipped'"
    )
    error_message: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Error details if processing failed"
    )
    
    # Link to normalized order after processing
    normalized_order_id: Optional[int] = Field(
        default=None,
        foreign_key="orders.order_id",
        index=True
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    processed_at: Optional[datetime] = Field(default=None)
    
    # Relationships
    platform: Optional[Platform] = Relationship(back_populates="raw_imports")
    seller: Optional[Seller] = Relationship(back_populates="raw_imports")
    normalized_order: Optional["Order"] = Relationship(
        back_populates="raw_import",
        sa_relationship_kwargs={"foreign_keys": "[PlatformRawImport.normalized_order_id]"},
    )


# =============================================================================
# Platform SKU / Translator Tables
# =============================================================================

class PlatformSKU(SQLModel, table=True):
    """
    Platform-specific product listings.
    
    This is the "Translator" table that maps platform SKUs to internal items.
    A platform listing can be a single item or a bundle of multiple items.
    """
    __tablename__ = "platform_sku"
    __table_args__ = (
        # Composite: seller + platform — listing lookup for a given seller on a platform
        Index("idx_platform_sku_seller", "seller_id", "platform_id"),
        # Composite: platform + SKU — the core SKU translation lookup
        Index("idx_platform_sku_lookup", "platform_id", "platform_sku"),
        # Partial: active SKUs only — all translation queries filter for active listings
        Index("idx_platform_sku_active", "platform_id", "seller_id", "platform_sku",
              postgresql_where=text("is_active = TRUE")),
    )

    listing_id: Optional[int] = Field(default=None, primary_key=True)
    platform_id: int = Field(foreign_key="platform.platform_id", index=True)
    seller_id: int = Field(foreign_key="seller.seller_id", index=True)
    
    # Platform-specific SKU and naming
    platform_sku: str = Field(max_length=200, index=True)
    platform_seller_sku_name: Optional[str] = Field(default=None, max_length=500)
    
    # Platform listing URL or ID
    platform_listing_url: Optional[str] = Field(default=None, max_length=1000)
    
    is_active: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    platform: Optional[Platform] = Relationship(back_populates="platform_skus")
    seller: Optional[Seller] = Relationship(back_populates="platform_skus")
    components: List["ListingComponent"] = Relationship(back_populates="listing")


class ListingComponent(SQLModel, table=True):
    """
    Links platform listings to internal items.
    
    Supports:
    - Single item listings (1 component)
    - Bundle/kit listings (multiple components)
    - Quantity multipliers (e.g., "Pack of 3")
    """
    __tablename__ = "listing_component"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    listing_id: int = Field(foreign_key="platform_sku.listing_id", index=True)
    item_id: int = Field(foreign_key="items.item_id", index=True)
    
    # Quantity of this item in the listing
    quantity: int = Field(default=1, ge=1)
    
    # Relationships
    listing: Optional[PlatformSKU] = Relationship(back_populates="components")


# =============================================================================
# Customer Table
# =============================================================================

class CustomerPlatform(SQLModel, table=True):
    """
    Customer data per platform.
    
    Stores customer information with platform-specific data in JSONB.
    """
    __tablename__ = "customer_platform"
    __table_args__ = (
        # GIN index on customer JSONB — enables queries on platform-specific customer fields
        Index("idx_customer_data_gin", "customer_data",
              postgresql_using="gin",
              postgresql_ops={"customer_data": "jsonb_path_ops"}),
    )

    customer_id: Optional[int] = Field(default=None, primary_key=True)
    customer_name: str = Field(max_length=200, index=True)
    platform_id: Optional[int] = Field(default=None, foreign_key="platform.platform_id")
    
    # JSONB for flexible platform-specific customer data
    # Example: {"platform_customer_id": "12345", "loyalty_tier": "Gold", "total_orders": 50}
    customer_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Platform-specific customer data"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    platform: Optional[Platform] = Relationship(back_populates="customers")


# =============================================================================
# Cancellation Tables
# =============================================================================

class CancellationReason(SQLModel, table=True):
    """
    Lookup table for order/item cancellation reasons.
    
    Examples: Customer Request, Seller Cancel, Refund Approved, 
    Delivery Failed, Customer Refused, Address Invalid, etc.
    """
    __tablename__ = "cancellation_reason"
    
    reason_id: Optional[int] = Field(default=None, primary_key=True)
    reason_code: str = Field(max_length=50, unique=True, index=True)
    reason_name: str = Field(max_length=200)
    reason_type: str = Field(
        max_length=50,
        index=True,
        description="Type: 'customer', 'seller', 'platform', 'delivery', 'system'"
    )
    
    # Inventory handling flags
    requires_inspection: bool = Field(
        default=False,
        description="If true, cancelled items need QC before restocking"
    )
    auto_restock: bool = Field(
        default=False,
        description="If true, items automatically return to available inventory"
    )
    
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    cancellations: List["OrderCancellation"] = Relationship(back_populates="reason")
    order_detail_cancellations: List["OrderDetail"] = Relationship(back_populates="cancellation_reason")


class OrderCancellation(SQLModel, table=True):
    """
    Tracks order and item-level cancellations with full audit trail.
    
    Features:
    - Supports both full order and partial item cancellations
    - Tracks inventory restock status
    - Links to platform refund/return references
    - Full audit trail with user and timestamp
    
    Example scenarios:
    - Full order cancellation before shipping
    - Partial cancellation (2 of 5 items cancelled)
    - Return-to-sender after delivery attempt
    - Platform-initiated refund
    """
    __tablename__ = "order_cancellations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Order reference (always required)
    order_id: int = Field(foreign_key="orders.order_id", index=True)
    
    # Item reference (null for full order cancellation)
    order_detail_id: Optional[int] = Field(
        default=None,
        foreign_key="order_details.detail_id",
        index=True,
        description="Specific line item cancelled (null = full order)"
    )
    
    # Cancellation details
    reason_id: int = Field(foreign_key="cancellation_reason.reason_id", index=True)
    cancellation_type: str = Field(
        max_length=50,
        index=True,
        description="Type: 'full_order', 'partial_item', 'return_to_sender'"
    )
    
    # For partial item cancellation
    cancelled_quantity: Optional[int] = Field(
        default=None,
        description="Quantity cancelled (for partial item cancellation)"
    )
    
    # Inventory handling
    restock_status: str = Field(
        default="pending",
        max_length=50,
        index=True,
        description="Status: 'pending', 'auto_restocked', 'pending_inspection', 'qc_passed', 'qc_failed', 'disposed'"
    )
    restocked_at: Optional[datetime] = Field(default=None)
    restocked_quantity: Optional[int] = Field(default=None)
    
    # Platform reference (for platform-initiated cancellations/refunds)
    platform_reference: Optional[str] = Field(
        default=None,
        max_length=200,
        index=True,
        description="Platform refund/return request ID"
    )
    platform_refund_amount: Optional[float] = Field(default=None)
    
    # Audit trail
    cancelled_by_user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.user_id",
        index=True
    )
    cancelled_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Additional notes
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    order: Optional["Order"] = Relationship(back_populates="cancellations")
    order_detail: Optional["OrderDetail"] = Relationship(back_populates="cancellations")
    reason: Optional[CancellationReason] = Relationship(back_populates="cancellations")


# =============================================================================
# Order Tables
# =============================================================================

class Order(SQLModel, table=True):
    """
    Main order entity.
    
    Contains shipping/recipient information, warehouse assignment,
    and links to platform/seller. Supports both shipping and billing
    addresses with raw platform data preservation.
    
    Features:
    - Warehouse assignment for fulfillment routing
    - Separate billing address (JSONB) from shipping address
    - Raw platform data preservation for auditing
    - Link to raw import record for traceability
    """
    __tablename__ = "orders"
    __table_args__ = (
        # GIN indexes on JSONB fields — platform data and billing address queries
        Index("idx_orders_platform_raw_gin", "platform_raw_data",
              postgresql_using="gin",
              postgresql_ops={"platform_raw_data": "jsonb_path_ops"}),
        Index("idx_orders_billing_address_gin", "billing_address",
              postgresql_using="gin",
              postgresql_ops={"billing_address": "jsonb_path_ops"}),
        # Composite: platform + store — filter all orders from a specific store
        Index("idx_orders_platform_store", "platform_id", "store_id"),
        # Composite: warehouse + status — fulfillment queue per warehouse
        Index("idx_orders_warehouse_status", "assigned_warehouse_id", "order_status"),
        # Composite: date + status — date-range reporting with status filter
        Index("idx_orders_date_status", "order_date", "order_status"),
        # Partial: pending orders only — the most common fulfillment queue query
        Index("idx_orders_pending", "order_id", "order_date",
              postgresql_where=text("order_status = 'pending'")),
    )

    order_id: Optional[int] = Field(default=None, primary_key=True)
    
    # Platform and store references
    store_id: Optional[int] = Field(default=None, foreign_key="seller.seller_id", index=True)
    platform_id: Optional[int] = Field(default=None, foreign_key="platform.platform_id", index=True)
    
    # Platform order reference
    platform_order_id: Optional[str] = Field(default=None, max_length=100, index=True)
    
    # Warehouse assignment for fulfillment
    assigned_warehouse_id: Optional[int] = Field(
        default=None,
        foreign_key="warehouse.id",
        index=True,
        description="Warehouse assigned to fulfill this order"
    )
    
    # Raw platform data preservation
    platform_raw_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Platform-specific order data (Shopee/Lazada variations, fees, etc.)"
    )
    
    # Link to raw import record
    raw_import_id: Optional[int] = Field(
        default=None,
        foreign_key="platform_raw_imports.id",
        index=True,
        description="Reference to the original raw import record"
    )
    
    # Recipient/Shipping Information
    phone_number: Optional[str] = Field(default=None, max_length=50)
    recipient_name: Optional[str] = Field(default=None, max_length=200)
    shipping_address: Optional[str] = Field(default=None, sa_column=Column(Text))
    shipping_postcode: Optional[str] = Field(default=None, max_length=20)
    shipping_state: Optional[str] = Field(default=None, max_length=100)
    country: Optional[str] = Field(default=None, max_length=100)
    
    # Billing address (separate from shipping)
    billing_address: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Billing address if different from shipping (JSONB for flexibility)"
    )
    
    # Order status
    order_status: Optional[str] = Field(default="pending", max_length=50, index=True)
    
    # Cancellation tracking
    cancellation_status: str = Field(
        default="none",
        max_length=50,
        index=True,
        description="Cancellation status: 'none', 'partial', 'full', 'return_pending'"
    )
    cancelled_at: Optional[datetime] = Field(default=None, index=True)
    cancelled_by_user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.user_id",
        description="User who initiated cancellation"
    )
    
    # Timestamps
    order_date: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    store: Optional[Seller] = Relationship(back_populates="orders")
    platform: Optional[Platform] = Relationship(back_populates="orders")
    details: List["OrderDetail"] = Relationship(back_populates="order")
    assigned_warehouse: Optional["Warehouse"] = Relationship(back_populates="orders")
    raw_import: Optional[PlatformRawImport] = Relationship(
        back_populates="normalized_order",
        sa_relationship_kwargs={"foreign_keys": "[PlatformRawImport.normalized_order_id]"},
    )
    cancellations: List["OrderCancellation"] = Relationship(back_populates="order")
    
    # Relationships for returns, exchanges, modifications, price adjustments
    returns: List["OrderReturn"] = Relationship(back_populates="order")
    exchanges_as_original: List["OrderExchange"] = Relationship(
        back_populates="original_order",
        sa_relationship_kwargs={"foreign_keys": "[OrderExchange.original_order_id]"}
    )
    exchanges_as_new: List["OrderExchange"] = Relationship(
        back_populates="new_order",
        sa_relationship_kwargs={"foreign_keys": "[OrderExchange.new_order_id]"}
    )
    modifications: List["OrderModification"] = Relationship(back_populates="order")
    price_adjustments: List["OrderPriceAdjustment"] = Relationship(back_populates="order")
    
    @property
    def is_cancelled(self) -> bool:
        """Check if order is fully cancelled."""
        return self.cancellation_status == "full"
    
    @property
    def has_cancellations(self) -> bool:
        """Check if order has any cancellations (partial or full)."""
        return self.cancellation_status != "none"
    
    @property
    def has_returns(self) -> bool:
        """Check if order has any returns."""
        return len(self.returns) > 0
    
    @property
    def has_exchanges(self) -> bool:
        """Check if order has any exchanges (as original order)."""
        return len(self.exchanges_as_original) > 0
    
    @property
    def can_be_modified(self) -> bool:
        """Check if order can be modified (only before shipping)."""
        return self.order_status in ("pending", "confirmed", "processing")


class OrderDetail(SQLModel, table=True):
    """
    Order line items with pricing and shipping information.
    
    Contains platform SKU data, amounts, tracking information,
    and links to resolved internal items after SKU translation.
    
    Features:
    - Platform SKU data preserved in JSONB
    - Tracking number with source identification (platform/courier/internal)
    - Link to resolved internal item after translation
    - Fulfillment status tracking per line item
    """
    __tablename__ = "order_details"
    __table_args__ = (
        # GIN index on platform SKU JSONB — enables querying raw platform product data
        Index("idx_order_details_sku_gin", "platform_sku_data",
              postgresql_using="gin",
              postgresql_ops={"platform_sku_data": "jsonb_path_ops"}),
        # Composite: order + item — fast line-item lookup after SKU translation
        Index("idx_order_details_order_item", "order_id", "resolved_item_id"),
        # Composite: fulfillment status + order — picking/packing queue queries
        Index("idx_order_details_fulfillment", "fulfillment_status", "order_id"),
    )

    detail_id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.order_id", index=True)
    
    # Platform SKU information (stored as JSON for flexibility)
    # Contains: {"platform_sku": "...", "sku_name": "...", "variation": "..."}
    platform_sku_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Platform SKU details (raw from platform)"
    )
    
    # Link to internal item after SKU translation
    resolved_item_id: Optional[int] = Field(
        default=None,
        foreign_key="items.item_id",
        index=True,
        description="Internal item ID after platform SKU translation"
    )
    
    # Pricing
    paid_amount: Optional[float] = Field(default=0.0)
    shipping_fee: Optional[float] = Field(default=0.0)
    discount: Optional[float] = Field(default=0.0)
    
    # Shipping/Courier Information
    courier_type: Optional[str] = Field(default=None, max_length=100)
    tracking_number: Optional[str] = Field(default=None, max_length=200, index=True)
    
    # Tracking number source identification
    tracking_source: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Source of tracking number: 'platform', 'courier', 'internal'"
    )
    
    # Quantity
    quantity: int = Field(default=1)
    
    # Fulfillment status per line item
    fulfillment_status: str = Field(
        default="pending",
        max_length=50,
        index=True,
        description="Fulfillment status: 'pending', 'picked', 'packed', 'shipped', 'delivered', 'cancelled', 'returned'"
    )
    
    # Item-level cancellation tracking
    is_cancelled: bool = Field(
        default=False,
        index=True,
        description="Whether this line item is cancelled"
    )
    cancelled_quantity: int = Field(
        default=0,
        description="Number of units cancelled (for partial cancellation)"
    )
    cancellation_reason_id: Optional[int] = Field(
        default=None,
        foreign_key="cancellation_reason.reason_id",
        index=True,
        description="Reason for cancellation"
    )
    cancelled_at: Optional[datetime] = Field(default=None)
    
    # Return tracking
    return_status: Optional[str] = Field(
        default=None,
        max_length=50,
        index=True,
        description="Return status: 'pending', 'in_transit', 'received', 'inspected', 'restocked', 'disposed'"
    )
    returned_quantity: int = Field(default=0)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    order: Optional[Order] = Relationship(back_populates="details")
    resolved_item: Optional["Item"] = Relationship(back_populates="order_details")
    trip_orders: List["TripOrder"] = Relationship(back_populates="order_detail")
    cancellation_reason: Optional[CancellationReason] = Relationship(back_populates="order_detail_cancellations")
    cancellations: List["OrderCancellation"] = Relationship(back_populates="order_detail")
    
    # Relationships for returns, exchanges, modifications, price adjustments
    returns: List["OrderReturn"] = Relationship(back_populates="order_detail")
    exchanges_as_original: List["OrderExchange"] = Relationship(
        back_populates="original_detail",
        sa_relationship_kwargs={"foreign_keys": "[OrderExchange.original_detail_id]"}
    )
    exchanges_as_new: List["OrderExchange"] = Relationship(
        back_populates="new_detail",
        sa_relationship_kwargs={"foreign_keys": "[OrderExchange.new_detail_id]"}
    )
    modifications: List["OrderModification"] = Relationship(back_populates="order_detail")
    price_adjustments: List["OrderPriceAdjustment"] = Relationship(back_populates="order_detail")
    
    @property
    def effective_quantity(self) -> int:
        """Get the effective quantity after cancellations."""
        return max(0, self.quantity - self.cancelled_quantity)
    
    @property
    def net_amount(self) -> float:
        """Calculate net amount after discounts."""
        return (self.paid_amount or 0) - (self.discount or 0)
    
    @property
    def has_active_return(self) -> bool:
        """Check if this line item has an active return."""
        return any(r.return_status not in ("completed", "cancelled", "rejected") for r in self.returns)
    
    @property
    def has_active_exchange(self) -> bool:
        """Check if this line item has an active exchange."""
        return any(e.exchange_status not in ("completed", "cancelled") for e in self.exchanges_as_original)


# Forward references for type checking
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.delivery import TripOrder
    from app.models.warehouse import Warehouse, SellerWarehouse
    from app.models.items import Item
    from app.models.order_operations import (
        OrderReturn,
        OrderExchange, 
        OrderModification,
        OrderPriceAdjustment,
    )
