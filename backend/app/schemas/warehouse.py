"""
WOMS Warehouse & Inventory Schemas

Request/response models for Warehouse, InventoryLocation, InventoryLevel,
InventoryMovement, and InventoryAlert endpoints.
"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, model_validator


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
    location_count: int = 0
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class WarehouseDuplicateResponse(BaseModel):
    """Response after a deep warehouse duplication."""
    original_id: int
    new_warehouse: WarehouseRead
    locations_copied: int


# ---------------------------------------------------------------------------
# Inventory Location
# ---------------------------------------------------------------------------

class InventoryLocationCreate(BaseModel):
    """POST /{warehouse_id}/locations request body."""
    section: Optional[str] = Field(None, max_length=50)
    zone: Optional[str] = Field(None, max_length=50)
    aisle: Optional[str] = Field(None, max_length=50)
    rack: Optional[str] = Field(None, max_length=50)
    bin: Optional[str] = Field(None, max_length=50)
    inventory_type_id: Optional[int] = None
    is_active: bool = True
    sort_order: Optional[int] = None


class InventoryLocationUpdate(BaseModel):
    """PATCH /locations/{id} request body."""
    section: Optional[str] = Field(None, max_length=50)
    zone: Optional[str] = Field(None, max_length=50)
    aisle: Optional[str] = Field(None, max_length=50)
    rack: Optional[str] = Field(None, max_length=50)
    bin: Optional[str] = Field(None, max_length=50)
    inventory_type_id: Optional[int] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


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
    display_code: Optional[str] = None
    is_active: bool = True
    sort_order: Optional[int] = None
    created_at: datetime


class LocationSummary(BaseModel):
    """Compact location info for enriched responses."""
    id: int
    code: str
    section: Optional[str] = None
    zone: Optional[str] = None
    aisle: Optional[str] = None
    rack: Optional[str] = None
    bin: Optional[str] = None


# ---------------------------------------------------------------------------
# Bulk Location Generation
# ---------------------------------------------------------------------------

class SegmentRange(BaseModel):
    """
    Specification for generating values for one location hierarchy level.

    Mode 1 — prefix + numeric range:
        {"prefix": "R", "start": 1, "end": 10, "pad": 2}  → R01, R02, ..., R10
        {"prefix": "",  "start": 1, "end": 5,  "pad": 3}  → 001, 002, ..., 005

    Mode 2 — explicit value list (overrides prefix/start/end):
        {"values": ["COLD", "DRY", "AMBIENT"]}
    """
    prefix: str = Field("", max_length=20)
    start: Optional[int] = Field(None, ge=0, le=9999)
    end: Optional[int] = Field(None, ge=0, le=9999)
    pad: int = Field(2, ge=0, le=6)
    values: Optional[list[str]] = Field(None, max_length=200)

    @model_validator(mode="after")
    def validate_range_or_values(self) -> "SegmentRange":
        if self.values is not None:
            if len(self.values) == 0:
                raise ValueError("values list must not be empty")
            for v in self.values:
                if len(v) > 50:
                    raise ValueError(f"Value '{v[:20]}...' exceeds 50 characters")
            return self
        if self.start is None or self.end is None:
            raise ValueError("Either 'values' or both 'start' and 'end' are required")
        if self.start > self.end:
            raise ValueError(f"start ({self.start}) must be <= end ({self.end})")
        # Check generated values fit VARCHAR(50)
        max_num_str = str(self.end).zfill(self.pad) if self.pad > 0 else str(self.end)
        if len(self.prefix) + len(max_num_str) > 50:
            raise ValueError(
                f"prefix + padded number would exceed 50 characters "
                f"({len(self.prefix)} + {len(max_num_str)} = {len(self.prefix) + len(max_num_str)})"
            )
        return self

    def expand(self) -> list[str]:
        """Expand this spec into a concrete list of string values."""
        if self.values is not None:
            return list(self.values)
        results = []
        for n in range(self.start, self.end + 1):  # type: ignore[arg-type]
            num_str = str(n).zfill(self.pad) if self.pad > 0 else str(n)
            results.append(f"{self.prefix}{num_str}")
        return results


class BulkGenerateRequest(BaseModel):
    """POST /{warehouse_id}/locations/bulk-generate request body."""
    section: Optional[SegmentRange] = None
    zone: Optional[SegmentRange] = None
    aisle: Optional[SegmentRange] = None
    rack: Optional[SegmentRange] = None
    bin: Optional[SegmentRange] = None
    inventory_type_id: Optional[int] = None
    is_active: bool = True

    @model_validator(mode="after")
    def at_least_one_range(self) -> "BulkGenerateRequest":
        segments = [self.section, self.zone, self.aisle, self.rack, self.bin]
        if not any(s is not None for s in segments):
            raise ValueError(
                "At least one segment range (section/zone/aisle/rack/bin) is required"
            )
        return self


class BulkGenerateError(BaseModel):
    """A single error from the bulk generation process."""
    location: str
    reason: str


class BulkGenerateResponse(BaseModel):
    """Response body for POST /{warehouse_id}/locations/bulk-generate."""
    warehouse_id: int
    total_requested: int
    created: int
    skipped: int
    errors: list[BulkGenerateError]


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
    reserved_quantity: int = 0
    reorder_point: Optional[int] = None
    safety_stock: Optional[int] = None
    max_stock: Optional[int] = None
    alert_triggered_at: Optional[datetime] = None
    alert_acknowledged: bool
    created_at: datetime
    updated_at: datetime


class InventoryLevelEnrichedRead(BaseModel):
    """Enriched inventory level with item name, location code, and stock status."""
    id: int
    location_id: int
    item_id: int
    item_name: str
    master_sku: str
    location: LocationSummary
    lot_id: Optional[int] = None
    quantity_available: int
    reserved_quantity: int = 0
    reorder_point: Optional[int] = None
    safety_stock: Optional[int] = None
    max_stock: Optional[int] = None
    stock_status: str
    alert_triggered_at: Optional[datetime] = None
    alert_acknowledged: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Inventory Movement
# ---------------------------------------------------------------------------

class MovementTypeRead(BaseModel):
    """Response body for a movement type."""
    id: int
    name: str


class InventoryMovementRead(BaseModel):
    """Response body for an inventory movement with joined item info."""
    id: int
    warehouse_id: int
    movement_type_id: int
    movement_type: MovementTypeRead
    item_id: int
    item_name: str
    master_sku: str
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    quantity: int
    is_inbound: bool
    created_at: datetime
    created_by: Optional[int] = None


class InventoryTransactionCreate(BaseModel):
    """A single transaction line within a movement."""
    location_id: int
    is_inbound: bool
    quantity_change: int = Field(..., gt=0)


class InventoryMovementCreate(BaseModel):
    """POST /warehouse/movements request body."""
    warehouse_id: int
    movement_type_id: int
    item_id: int
    transactions: list[InventoryTransactionCreate] = Field(..., min_length=1)
    reference_number: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=500)


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
    resolution_notes: Optional[str] = None
    resolved_by_user_id: Optional[int] = None
    created_at: datetime


class AlertResolveRequest(BaseModel):
    """PATCH /warehouse/alerts/{id}/resolve request body."""
    resolution_notes: Optional[str] = Field(None, max_length=500)


# ---------------------------------------------------------------------------
# Stock Reservation / Release / Bundle Fulfill
# ---------------------------------------------------------------------------

class ReserveRequest(BaseModel):
    """POST /warehouse/reserve request body (standalone or single-item reservation)."""
    item_id: int
    quantity: int = Field(..., gt=0)
    warehouse_id: int


class ReserveResponse(BaseModel):
    """Response after a successful reservation."""
    item_id: int
    quantity_reserved: int
    warehouse_id: int


class ReleaseRequest(BaseModel):
    """POST /warehouse/release request body."""
    item_id: int
    quantity: int = Field(..., gt=0)
    warehouse_id: int


class RenameLevelRequest(BaseModel):
    """PATCH /{warehouse_id}/locations/rename-level request body."""
    level: str = Field(..., description="Hierarchy level: section, zone, aisle, rack, or bin")
    old_value: str = Field(..., max_length=50)
    new_value: str = Field(..., min_length=1, max_length=50)
    # Parent path context — narrows which locations get updated
    section: Optional[str] = None
    zone: Optional[str] = None
    aisle: Optional[str] = None
    rack: Optional[str] = None

    @model_validator(mode="after")
    def validate_level(self) -> "RenameLevelRequest":
        valid = {"section", "zone", "aisle", "rack", "bin"}
        if self.level not in valid:
            raise ValueError(f"level must be one of {valid}")
        if self.old_value == self.new_value:
            raise ValueError("new_value must differ from old_value")
        return self


class RenameLevelResponse(BaseModel):
    """Response body for PATCH /{warehouse_id}/locations/rename-level."""
    updated_count: int
    level: str
    old_value: str
    new_value: str


class BulkLocationUpdateItem(BaseModel):
    """One item in a bulk location update request."""
    id: int
    section: Optional[str] = Field(None, max_length=50)
    zone: Optional[str] = Field(None, max_length=50)
    aisle: Optional[str] = Field(None, max_length=50)
    rack: Optional[str] = Field(None, max_length=50)
    bin: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class BulkLocationUpdateRequest(BaseModel):
    """PATCH /{warehouse_id}/locations/bulk-update request body."""
    locations: List[BulkLocationUpdateItem]


class BulkLocationUpdateResult(BaseModel):
    """Per-row result returned from bulk-update."""
    id: int
    success: bool
    error: Optional[str] = None


class BulkLocationUpdateResponse(BaseModel):
    """Response body for PATCH /{warehouse_id}/locations/bulk-update."""
    updated: int
    failed: int
    results: List[BulkLocationUpdateResult]


class BundleFulfillRequest(BaseModel):
    """POST /warehouse/fulfill/bundle request body."""
    bundle_item_id: int
    bundle_qty_sold: int = Field(..., gt=0)
    warehouse_id: int
    order_reference: str = Field(..., max_length=100)
