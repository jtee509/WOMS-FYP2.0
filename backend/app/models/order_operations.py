"""
WOMS Order Operations Module Models

This module contains models for order returns, exchanges, modifications,
and price adjustments:
- ReturnReason: Lookup table for return reasons
- OrderReturn: Tracks return workflow and inspection
- ExchangeReason: Lookup table for exchange reasons
- OrderExchange: Tracks exchange relationships and value adjustments
- OrderModification: Full audit trail for order changes
- OrderPriceAdjustment: Tracks price adjustments (top-ups, reductions, waivers)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB


# =============================================================================
# Return Tables
# =============================================================================

class ReturnReason(SQLModel, table=True):
    """
    Lookup table for order return reasons.
    
    Examples: Wrong Item, Damaged, Not as Described, Changed Mind, etc.
    """
    __tablename__ = "return_reason"
    __table_args__ = (
        # Partial: active reasons only — lookup forms only show active options
        Index("idx_return_reason_active", "is_active",
              postgresql_where=text("is_active = TRUE")),
    )

    reason_id: Optional[int] = Field(default=None, primary_key=True)
    reason_code: str = Field(max_length=50, unique=True, index=True)
    reason_name: str = Field(max_length=200)
    reason_type: str = Field(
        max_length=50,
        index=True,
        description="Type: 'customer', 'platform', 'delivery', 'quality'"
    )
    
    # Inspection flag
    requires_inspection: bool = Field(
        default=True,
        description="Whether returned items need QC inspection before restocking"
    )
    
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    returns: List["OrderReturn"] = Relationship(back_populates="reason")


class OrderReturn(SQLModel, table=True):
    """
    Tracks order return workflow including inspection and restocking.
    
    Workflow: requested -> approved -> in_transit -> received -> inspecting -> completed
    
    Features:
    - Return type classification (customer, delivery failed, platform, quality)
    - Inspection workflow with pass/fail/partial outcomes
    - Restock decision tracking (restock, dispose, repair, exchange)
    - Platform return reference for marketplace returns
    """
    __tablename__ = "order_returns"
    __table_args__ = (
        # Partial: returns with platform reference — marketplace return portal lookups
        Index("idx_order_returns_platform_ref", "platform_return_reference",
              postgresql_where=text("platform_return_reference IS NOT NULL")),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Order references
    order_id: int = Field(foreign_key="orders.order_id", index=True)
    order_detail_id: int = Field(foreign_key="order_details.detail_id", index=True)
    
    # Return classification
    return_type: str = Field(
        max_length=50,
        index=True,
        description="Type: 'customer_return', 'delivery_failed', 'platform_return', 'quality_issue'"
    )
    return_reason_id: Optional[int] = Field(
        default=None,
        foreign_key="return_reason.reason_id"
    )
    
    # Return workflow status
    return_status: str = Field(
        default="requested",
        max_length=50,
        index=True,
        description="Status: 'requested', 'approved', 'rejected', 'in_transit', 'received', 'inspecting', 'completed', 'cancelled'"
    )
    
    # Quantity tracking
    returned_quantity: int = Field(default=1, ge=1)
    
    # Inspection workflow
    inspection_status: Optional[str] = Field(
        default="pending",
        max_length=50,
        index=True,
        description="QC result: 'pending', 'passed', 'failed', 'partial'"
    )
    inspection_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    inspected_at: Optional[datetime] = Field(default=None)
    inspected_by_user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.user_id"
    )
    
    # Restock decision after inspection
    restock_decision: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Post-inspection: 'restock', 'dispose', 'repair', 'exchange', 'pending'"
    )
    restocked_quantity: int = Field(default=0)
    restocked_at: Optional[datetime] = Field(default=None)
    
    # Platform integration
    platform_return_reference: Optional[str] = Field(
        default=None,
        max_length=200,
        index=True,
        description="Platform return/refund request ID"
    )
    
    # Audit trail
    initiated_by_user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.user_id"
    )
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Timestamps
    requested_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    approved_at: Optional[datetime] = Field(default=None)
    received_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    order: Optional["Order"] = Relationship(back_populates="returns")
    order_detail: Optional["OrderDetail"] = Relationship(back_populates="returns")
    reason: Optional[ReturnReason] = Relationship(back_populates="returns")
    exchanges: List["OrderExchange"] = Relationship(back_populates="return_record")
    modifications: List["OrderModification"] = Relationship(back_populates="related_return")
    
    @property
    def is_completed(self) -> bool:
        """Check if return is completed."""
        return self.return_status == "completed"
    
    @property
    def needs_inspection(self) -> bool:
        """Check if return needs inspection."""
        return self.return_status == "received" and self.inspection_status == "pending"


# =============================================================================
# Exchange Tables
# =============================================================================

class ExchangeReason(SQLModel, table=True):
    """
    Lookup table for order exchange reasons.
    
    Examples: Wrong Size, Wrong Color, Defective, Customer Preference, etc.
    """
    __tablename__ = "exchange_reason"
    __table_args__ = (
        # Partial: active reasons only — lookup forms only show active options
        Index("idx_exchange_reason_active", "is_active",
              postgresql_where=text("is_active = TRUE")),
    )

    reason_id: Optional[int] = Field(default=None, primary_key=True)
    reason_code: str = Field(max_length=50, unique=True, index=True)
    reason_name: str = Field(max_length=200)
    
    # Whether original item must be returned for exchange
    requires_return: bool = Field(
        default=True,
        description="Whether original item must be returned for exchange"
    )
    
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    exchanges: List["OrderExchange"] = Relationship(back_populates="reason")


class OrderExchange(SQLModel, table=True):
    """
    Tracks order exchange relationships and value adjustments.
    
    Supports:
    - Same value exchanges (equal swap)
    - Different value exchanges (price difference tracking)
    - In-place exchanges (modify existing order)
    - Linked exchanges (create new order)
    
    Features:
    - Value difference calculation (customer pays more or gets credit)
    - Link to return record if original item needs to come back
    - Platform exchange reference for marketplace exchanges
    """
    __tablename__ = "order_exchanges"
    __table_args__ = (
        # Partial indexes: only index rows where the optional FK is set
        # Avoids bloating the index with NULL entries which are never queried
        Index("idx_order_exchanges_new_order", "new_order_id",
              postgresql_where=text("new_order_id IS NOT NULL")),
        Index("idx_order_exchanges_return", "return_id",
              postgresql_where=text("return_id IS NOT NULL")),
        Index("idx_order_exchanges_platform_ref", "platform_exchange_reference",
              postgresql_where=text("platform_exchange_reference IS NOT NULL")),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Original order/item references
    original_order_id: int = Field(foreign_key="orders.order_id", index=True)
    original_detail_id: int = Field(foreign_key="order_details.detail_id", index=True)
    
    # Exchange classification
    exchange_type: str = Field(
        max_length=50,
        index=True,
        description="Type: 'same_value', 'different_value', 'in_place'"
    )
    exchange_reason_id: Optional[int] = Field(
        default=None,
        foreign_key="exchange_reason.reason_id"
    )
    
    # Exchange workflow status
    exchange_status: str = Field(
        default="requested",
        max_length=50,
        index=True,
        description="Status: 'requested', 'approved', 'processing', 'shipped', 'completed', 'cancelled'"
    )
    
    # For linked exchanges (new order created)
    new_order_id: Optional[int] = Field(
        default=None,
        foreign_key="orders.order_id",
        index=True
    )
    new_detail_id: Optional[int] = Field(
        default=None,
        foreign_key="order_details.detail_id"
    )
    
    # For in-place exchanges (same order modified)
    exchanged_item_id: Optional[int] = Field(
        default=None,
        foreign_key="items.item_id",
        description="New item ID for in-place exchange"
    )
    exchanged_quantity: int = Field(default=1, ge=1)
    
    # Value adjustment tracking
    original_value: float = Field(default=0.0)
    new_value: float = Field(default=0.0)
    value_difference: float = Field(
        default=0.0,
        description="Positive = customer pays more, Negative = credit/refund"
    )
    adjustment_status: str = Field(
        default="pending",
        max_length=50,
        description="Payment status: 'pending', 'paid', 'waived', 'credited', 'not_applicable'"
    )
    
    # Link to return record if original item needs to come back
    return_id: Optional[int] = Field(
        default=None,
        foreign_key="order_returns.id",
        index=True
    )
    
    # Platform integration
    platform_exchange_reference: Optional[str] = Field(
        default=None,
        max_length=200,
        index=True,
        description="Platform exchange request ID"
    )
    
    # Audit trail
    initiated_by_user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.user_id"
    )
    approved_by_user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.user_id"
    )
    notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Timestamps
    requested_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    approved_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    original_order: Optional["Order"] = Relationship(
        back_populates="exchanges_as_original",
        sa_relationship_kwargs={"foreign_keys": "[OrderExchange.original_order_id]"}
    )
    original_detail: Optional["OrderDetail"] = Relationship(
        back_populates="exchanges_as_original",
        sa_relationship_kwargs={"foreign_keys": "[OrderExchange.original_detail_id]"}
    )
    new_order: Optional["Order"] = Relationship(
        back_populates="exchanges_as_new",
        sa_relationship_kwargs={"foreign_keys": "[OrderExchange.new_order_id]"}
    )
    new_detail: Optional["OrderDetail"] = Relationship(
        back_populates="exchanges_as_new",
        sa_relationship_kwargs={"foreign_keys": "[OrderExchange.new_detail_id]"}
    )
    reason: Optional[ExchangeReason] = Relationship(back_populates="exchanges")
    return_record: Optional[OrderReturn] = Relationship(back_populates="exchanges")
    price_adjustments: List["OrderPriceAdjustment"] = Relationship(back_populates="related_exchange")
    modifications: List["OrderModification"] = Relationship(back_populates="related_exchange")
    
    @property
    def is_same_value(self) -> bool:
        """Check if this is a same-value exchange."""
        return self.exchange_type == "same_value" or self.value_difference == 0
    
    @property
    def requires_payment(self) -> bool:
        """Check if customer needs to pay more."""
        return self.value_difference > 0 and self.adjustment_status == "pending"


# =============================================================================
# Order Modification Tables
# =============================================================================

class OrderModification(SQLModel, table=True):
    """
    Full audit trail for all order changes.
    
    Tracks:
    - Address/recipient changes
    - Item additions, removals, and changes
    - Quantity modifications
    - Pricing adjustments
    
    Features:
    - Stores old and new values as JSONB for flexibility
    - Links to related exchanges/returns if applicable
    - User and timestamp tracking
    """
    __tablename__ = "order_modifications"
    __table_args__ = (
        # GIN indexes on JSONB diff fields — enables querying what changed (before/after)
        Index("idx_order_modifications_old_value", "old_value",
              postgresql_using="gin",
              postgresql_ops={"old_value": "jsonb_path_ops"}),
        Index("idx_order_modifications_new_value", "new_value",
              postgresql_using="gin",
              postgresql_ops={"new_value": "jsonb_path_ops"}),
        # Partial indexes: skip NULL FK rows — detail/exchange/return are all optional
        Index("idx_order_modifications_detail_id", "order_detail_id",
              postgresql_where=text("order_detail_id IS NOT NULL")),
        Index("idx_order_modifications_exchange", "related_exchange_id",
              postgresql_where=text("related_exchange_id IS NOT NULL")),
        Index("idx_order_modifications_return", "related_return_id",
              postgresql_where=text("related_return_id IS NOT NULL")),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Order references
    order_id: int = Field(foreign_key="orders.order_id", index=True)
    order_detail_id: Optional[int] = Field(
        default=None,
        foreign_key="order_details.detail_id",
        index=True,
        description="Specific line item modified (null = order-level change)"
    )
    
    # Modification classification
    modification_type: str = Field(
        max_length=50,
        index=True,
        description="Type: 'address', 'recipient', 'item_add', 'item_remove', 'item_change', 'quantity', 'pricing', 'shipping', 'other'"
    )
    
    # Field-level tracking
    field_changed: str = Field(
        max_length=100,
        index=True,
        description="Specific field changed (e.g., 'shipping_address', 'resolved_item_id', 'quantity')"
    )
    old_value: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Previous value stored as JSONB"
    )
    new_value: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="New value stored as JSONB"
    )
    
    # Reason for modification
    modification_reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Related records (if modification triggered by exchange/return)
    related_exchange_id: Optional[int] = Field(
        default=None,
        foreign_key="order_exchanges.id",
        index=True
    )
    related_return_id: Optional[int] = Field(
        default=None,
        foreign_key="order_returns.id",
        index=True
    )
    
    # Audit trail
    modified_by_user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.user_id",
        index=True
    )
    modified_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    order: Optional["Order"] = Relationship(back_populates="modifications")
    order_detail: Optional["OrderDetail"] = Relationship(back_populates="modifications")
    related_exchange: Optional[OrderExchange] = Relationship(back_populates="modifications")
    related_return: Optional[OrderReturn] = Relationship(back_populates="modifications")
    price_adjustments: List["OrderPriceAdjustment"] = Relationship(back_populates="related_modification")


class OrderPriceAdjustment(SQLModel, table=True):
    """
    Tracks order price adjustments including top-ups, reductions, and waivers.
    
    Types:
    - top_up: Customer pays additional amount
    - reduction: Customer pays less / gets credit
    - waived: No charge for difference
    - exchange_difference: Price difference from exchange
    - discount: Additional discount applied
    - fee: Additional fee applied
    - correction: Price correction
    
    Features:
    - Original, adjustment, and final amount tracking
    - Links to related exchanges/modifications
    - Status workflow (pending -> applied/cancelled/refunded)
    """
    __tablename__ = "order_price_adjustments"
    __table_args__ = (
        # Partial indexes: skip NULL FK rows — detail/exchange/modification are optional
        Index("idx_order_price_adj_detail_id", "order_detail_id",
              postgresql_where=text("order_detail_id IS NOT NULL")),
        Index("idx_order_price_adj_exchange", "related_exchange_id",
              postgresql_where=text("related_exchange_id IS NOT NULL")),
        Index("idx_order_price_adj_modification", "related_modification_id",
              postgresql_where=text("related_modification_id IS NOT NULL")),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Order references
    order_id: int = Field(foreign_key="orders.order_id", index=True)
    order_detail_id: Optional[int] = Field(
        default=None,
        foreign_key="order_details.detail_id",
        index=True
    )
    
    # Adjustment classification
    adjustment_type: str = Field(
        max_length=50,
        index=True,
        description="Type: 'top_up', 'reduction', 'waived', 'exchange_difference', 'discount', 'fee', 'correction'"
    )
    
    # Adjustment details
    adjustment_reason: str = Field(sa_column=Column(Text, nullable=False))
    original_amount: float = Field(default=0.0)
    adjustment_amount: float = Field(
        default=0.0,
        description="Positive = increase, Negative = decrease"
    )
    final_amount: float = Field(default=0.0)
    
    # Related records
    related_exchange_id: Optional[int] = Field(
        default=None,
        foreign_key="order_exchanges.id",
        index=True
    )
    related_modification_id: Optional[int] = Field(
        default=None,
        foreign_key="order_modifications.id",
        index=True
    )
    
    # Workflow status
    status: str = Field(
        default="pending",
        max_length=50,
        index=True,
        description="Status: 'pending', 'applied', 'cancelled', 'refunded'"
    )
    
    # Audit trail
    created_by_user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.user_id"
    )
    applied_by_user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.user_id"
    )
    applied_at: Optional[datetime] = Field(default=None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    order: Optional["Order"] = Relationship(back_populates="price_adjustments")
    order_detail: Optional["OrderDetail"] = Relationship(back_populates="price_adjustments")
    related_exchange: Optional[OrderExchange] = Relationship(back_populates="price_adjustments")
    related_modification: Optional[OrderModification] = Relationship(back_populates="price_adjustments")
    
    @property
    def is_applied(self) -> bool:
        """Check if adjustment has been applied."""
        return self.status == "applied"
    
    @property
    def is_increase(self) -> bool:
        """Check if this is a price increase."""
        return self.adjustment_amount > 0


# Forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.orders import Order, OrderDetail
