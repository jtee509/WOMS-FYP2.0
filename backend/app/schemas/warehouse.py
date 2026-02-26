"""
WOMS Warehouse & Inventory Schemas

Request/response models for Warehouse, InventoryLocation, InventoryLevel endpoints.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Warehouse
# ---------------------------------------------------------------------------

class WarehouseCreate(BaseModel):
    """POST /warehouse request body."""
    warehouse_name: str = Field(..., max_length=200)
    address: Optional[dict[str, Any]] = None
    is_active: bool = True


class WarehouseUpdate(BaseModel):
    """PATCH /warehouse/{id} request body."""
    warehouse_name: Optional[str] = Field(None, max_length=200)
    address: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class WarehouseRead(BaseModel):
    """Response body for a single warehouse."""
    id: int
    warehouse_name: str
    address: Optional[dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Inventory Location
# ---------------------------------------------------------------------------

class InventoryLocationRead(BaseModel):
    """Response body for an inventory location."""
    id: int
    warehouse_id: int
    section: Optional[str] = None
    zone: Optional[str] = None
    aisle: Optional[str] = None
    rack: Optional[str] = None
    bin: Optional[str] = None
    inventory_type_id: Optional[int] = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Inventory Level
# ---------------------------------------------------------------------------

class InventoryLevelRead(BaseModel):
    """Response body for current stock at a location."""
    id: int
    location_id: int
    item_id: int
    lot_id: Optional[int] = None
    quantity_available: int
    reorder_point: Optional[int] = None
    safety_stock: Optional[int] = None
    max_stock: Optional[int] = None
    alert_triggered_at: Optional[datetime] = None
    alert_acknowledged: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Inventory Alert
# ---------------------------------------------------------------------------

class InventoryAlertRead(BaseModel):
    """Response body for an inventory alert."""
    id: int
    inventory_level_id: int
    item_id: int
    warehouse_id: int
    alert_type: str
    current_quantity: int
    threshold_quantity: int
    alert_message: Optional[str] = None
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    created_at: datetime
