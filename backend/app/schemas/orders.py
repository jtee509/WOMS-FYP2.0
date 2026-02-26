"""
WOMS Order Schemas

Request/response models for Orders and OrderDetails endpoints.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# OrderDetail
# ---------------------------------------------------------------------------

class OrderDetailCreate(BaseModel):
    """Nested in OrderCreate — one line item."""
    platform_sku_data: Optional[dict[str, Any]] = None
    resolved_item_id: Optional[int] = None
    paid_amount: float = 0.0
    shipping_fee: float = 0.0
    discount: float = 0.0
    courier_type: Optional[str] = Field(None, max_length=100)
    tracking_number: Optional[str] = Field(None, max_length=200)
    tracking_source: Optional[str] = Field(None, max_length=50)
    quantity: int = 1


class OrderDetailUpdate(BaseModel):
    """PATCH fields for a single order detail."""
    resolved_item_id: Optional[int] = None
    paid_amount: Optional[float] = None
    shipping_fee: Optional[float] = None
    discount: Optional[float] = None
    courier_type: Optional[str] = Field(None, max_length=100)
    tracking_number: Optional[str] = Field(None, max_length=200)
    tracking_source: Optional[str] = Field(None, max_length=50)
    quantity: Optional[int] = None
    fulfillment_status: Optional[str] = Field(None, max_length=50)


class OrderDetailRead(BaseModel):
    """Response body for an order line item."""
    detail_id: int
    order_id: int
    platform_sku_data: Optional[dict[str, Any]] = None
    resolved_item_id: Optional[int] = None
    paid_amount: Optional[float] = None
    shipping_fee: Optional[float] = None
    discount: Optional[float] = None
    courier_type: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_source: Optional[str] = None
    quantity: int
    fulfillment_status: str
    is_cancelled: bool
    cancelled_quantity: int
    return_status: Optional[str] = None
    returned_quantity: int
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class OrderCreate(BaseModel):
    """POST /orders request body."""
    store_id: Optional[int] = None
    platform_id: Optional[int] = None
    platform_order_id: Optional[str] = Field(None, max_length=100)
    assigned_warehouse_id: Optional[int] = None
    phone_number: Optional[str] = Field(None, max_length=50)
    recipient_name: Optional[str] = Field(None, max_length=200)
    shipping_address: Optional[str] = None
    shipping_postcode: Optional[str] = Field(None, max_length=20)
    shipping_state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    billing_address: Optional[dict[str, Any]] = None
    platform_raw_data: Optional[dict[str, Any]] = None
    order_status: str = "pending"
    order_date: Optional[datetime] = None
    details: list[OrderDetailCreate] = Field(default_factory=list)


class OrderUpdate(BaseModel):
    """PATCH /orders/{id} request body. All fields optional."""
    assigned_warehouse_id: Optional[int] = None
    phone_number: Optional[str] = Field(None, max_length=50)
    recipient_name: Optional[str] = Field(None, max_length=200)
    shipping_address: Optional[str] = None
    shipping_postcode: Optional[str] = Field(None, max_length=20)
    shipping_state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    billing_address: Optional[dict[str, Any]] = None
    order_status: Optional[str] = Field(None, max_length=50)


class OrderRead(BaseModel):
    """Response body for a single order."""
    order_id: int
    store_id: Optional[int] = None
    platform_id: Optional[int] = None
    platform_order_id: Optional[str] = None
    assigned_warehouse_id: Optional[int] = None
    raw_import_id: Optional[int] = None
    phone_number: Optional[str] = None
    recipient_name: Optional[str] = None
    shipping_address: Optional[str] = None
    shipping_postcode: Optional[str] = None
    shipping_state: Optional[str] = None
    country: Optional[str] = None
    billing_address: Optional[dict[str, Any]] = None
    platform_raw_data: Optional[dict[str, Any]] = None
    order_status: Optional[str] = None
    cancellation_status: str
    cancelled_at: Optional[datetime] = None
    order_date: datetime
    created_at: datetime
    updated_at: datetime
    details: list[OrderDetailRead] = Field(default_factory=list)


class OrderListItem(BaseModel):
    """Lightweight order for list views (no details, no JSONB)."""
    order_id: int
    store_id: Optional[int] = None
    platform_id: Optional[int] = None
    platform_order_id: Optional[str] = None
    assigned_warehouse_id: Optional[int] = None
    recipient_name: Optional[str] = None
    order_status: Optional[str] = None
    cancellation_status: str
    order_date: datetime
    created_at: datetime
