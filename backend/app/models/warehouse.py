"""
WOMS Warehouse Module Models

This module contains all warehouse and inventory-related models:
- Warehouse: Physical warehouse locations
- InventoryLocation: Specific locations within warehouses (Zone/Aisle/Rack/Bin)
- InventoryType: Types of inventory locations
- InventoryTransaction: Stock movement transactions
- InventoryLevel: Current stock levels at each location with alert thresholds
- StockLot: Batch/Lot tracking for items
- InventoryMovement: Movement records
- MovementType: Types of movements
- InventoryReplenishmentHistory: Replenishment trigger tracking
- InventoryAlert: Low stock and inventory alert tracking
- SellerWarehouse: Seller-to-warehouse fulfillment routing
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Index, text
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB


# =============================================================================
# Warehouse & Location Tables
# =============================================================================

class Warehouse(SQLModel, table=True):
    """
    Physical warehouse location.
    
    Features:
    - JSONB address field for flexible address storage
    - Active/inactive status for warehouse management
    """
    __tablename__ = "warehouse"
    __table_args__ = (
        # GIN index on JSONB address — enables city/state/postcode queries
        Index("idx_warehouse_address_gin", "address",
              postgresql_using="gin",
              postgresql_ops={"address": "jsonb_path_ops"}),
        # Partial: only active warehouses (most queries filter is_active=TRUE)
        Index("idx_warehouse_active", "id", "warehouse_name",
              postgresql_where=text("is_active = TRUE")),
        # Partial: exclude soft-deleted rows from all standard queries
        Index("idx_warehouse_not_deleted", "id",
              postgresql_where=text("deleted_at IS NULL")),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    warehouse_name: str = Field(max_length=200, unique=True, index=True)
    
    # JSONB address for flexible storage
    # Example: {"street": "123 Main St", "city": "KL", "state": "Selangor", "postcode": "50000"}
    address: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="JSONB address data"
    )
    
    is_active: bool = Field(default=True, index=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    # Soft delete — NULL means live; non-NULL means deleted
    deleted_at: Optional[datetime] = Field(default=None, index=True)

    # Relationships
    locations: List["InventoryLocation"] = Relationship(back_populates="warehouse")
    lorries: List["Lorry"] = Relationship(back_populates="warehouse")
    drivers: List["Driver"] = Relationship(back_populates="warehouse")
    orders: List["Order"] = Relationship(back_populates="assigned_warehouse")
    seller_warehouses: List["SellerWarehouse"] = Relationship(back_populates="warehouse")
    inventory_alerts: List["InventoryAlert"] = Relationship(back_populates="warehouse")


class InventoryType(SQLModel, table=True):
    """
    Types of inventory locations.
    
    Examples: Bulk Storage, Pick Face, Receiving, Staging, Shipping, etc.
    """
    __tablename__ = "inventory_type"
    
    inventory_type_id: Optional[int] = Field(default=None, primary_key=True)
    inventory_type_name: str = Field(max_length=100, unique=True, index=True)
    
    # Relationships
    locations: List["InventoryLocation"] = Relationship(back_populates="inventory_type")


class InventoryLocation(SQLModel, table=True):
    """
    Specific location within a warehouse.

    Follows standard warehouse addressing: Section > Zone > Aisle > Rack > Bin.

    The display_code column is auto-populated by a BEFORE INSERT trigger
    (generate_location_display_code) that concatenates non-null hierarchy
    segments with hyphens, e.g. "A1-Z1-A01-R5-B12".
    """
    __tablename__ = "inventory_location"
    __table_args__ = (
        # Composite UNIQUE — no two locations can share the same physical
        # address within a single warehouse.  COALESCE handles NULLs so
        # partial addresses still participate in the constraint.
        Index(
            "uq_location_address",
            "warehouse_id",
            text("COALESCE(section, '')"),
            text("COALESCE(zone, '')"),
            text("COALESCE(aisle, '')"),
            text("COALESCE(rack, '')"),
            text("COALESCE(bin, '')"),
            unique=True,
        ),
        # Partial: active locations only — hot-path optimisation
        Index(
            "idx_inventory_location_active",
            "warehouse_id", "is_active",
            postgresql_where=text("is_active = TRUE"),
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    warehouse_id: int = Field(foreign_key="warehouse.id", index=True)

    # Location hierarchy
    section: Optional[str] = Field(default=None, max_length=50, index=True)
    zone: Optional[str] = Field(default=None, max_length=50, index=True)
    aisle: Optional[str] = Field(default=None, max_length=50, index=True)
    rack: Optional[str] = Field(default=None, max_length=50, index=True)
    bin: Optional[str] = Field(default=None, max_length=50, index=True)

    inventory_type_id: Optional[int] = Field(
        default=None,
        foreign_key="inventory_type.inventory_type_id"
    )

    # Display code — auto-generated by trigger: "Section-Zone-Aisle-Rack-Bin"
    display_code: Optional[str] = Field(default=None, max_length=255)

    # Operational status — FALSE = temporarily decommissioned (e.g. re-racking)
    is_active: bool = Field(default=True, index=True)

    # User-defined ordering for pick-path priority
    sort_order: Optional[int] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # Soft delete — NULL means live; non-NULL means deleted
    deleted_at: Optional[datetime] = Field(default=None, index=True)

    # Relationships
    warehouse: Optional[Warehouse] = Relationship(back_populates="locations")
    inventory_type: Optional[InventoryType] = Relationship(back_populates="locations")
    inventory_levels: List["InventoryLevel"] = Relationship(back_populates="location")
    transactions: List["InventoryTransaction"] = Relationship(back_populates="location")

    @property
    def full_location_code(self) -> str:
        """Generate full location code from hierarchy (in-memory fallback)."""
        parts = [self.section, self.zone, self.aisle, self.rack, self.bin]
        return "-".join(p for p in parts if p)


# =============================================================================
# Movement & Transaction Tables
# =============================================================================

class MovementType(SQLModel, table=True):
    """
    Types of inventory movements.
    
    Examples: Receipt, Shipment, Transfer, Adjustment, Return, Cycle Count, etc.
    """
    __tablename__ = "movement_type"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    movement_name: str = Field(max_length=100, unique=True, index=True)
    
    # Relationships
    movements: List["InventoryMovement"] = Relationship(back_populates="movement_type")


class InventoryMovement(SQLModel, table=True):
    """
    Inventory movement record.
    
    Groups related transactions (e.g., a transfer has source and destination).
    """
    __tablename__ = "inventory_movements"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    movement_type_id: int = Field(foreign_key="movement_type.id", index=True)
    
    # Reference to source document (order_id, transfer_id, etc.)
    reference_id: Optional[str] = Field(default=None, max_length=100, index=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    movement_type: Optional[MovementType] = Relationship(back_populates="movements")
    transactions: List["InventoryTransaction"] = Relationship(back_populates="movement")


class InventoryTransaction(SQLModel, table=True):
    """
    Individual inventory transaction record.
    
    Records each stock movement in/out of a location.
    """
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        # Composite: movement + date DESC — transaction history per movement
        Index("idx_transactions_movement_date", "movement_id", "created_at"),
        # Composite: item + location + date DESC — item movement history
        Index("idx_transactions_item_location", "item_id", "location_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="items.item_id", index=True)
    location_id: int = Field(foreign_key="inventory_location.id", index=True)
    movement_id: Optional[int] = Field(
        default=None, 
        foreign_key="inventory_movements.id",
        index=True
    )
    
    # Direction: True = In (receipt), False = Out (shipment)
    is_inbound: bool = Field(description="True for inbound, False for outbound")
    quantity_change: int = Field(description="Quantity changed (always positive)")
    
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    location: Optional[InventoryLocation] = Relationship(back_populates="transactions")
    movement: Optional[InventoryMovement] = Relationship(back_populates="transactions")


# =============================================================================
# Stock Level & Lot Tables
# =============================================================================

class StockLot(SQLModel, table=True):
    """
    Batch/Lot tracking for items.
    
    Supports:
    - Batch numbers (for batch-tracked items)
    - Serial numbers (for serialized items)
    - Unique barcodes
    - Expiry date tracking (for FEFO)
    """
    __tablename__ = "stock_lots"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="items.item_id", index=True)
    
    # Lot/Batch identification
    batch_number: Optional[str] = Field(default=None, max_length=100, index=True)
    serial_number: Optional[str] = Field(default=None, max_length=100, unique=True)
    unique_barcode: Optional[str] = Field(default=None, max_length=200, unique=True)
    
    # Expiry tracking (for FEFO - First Expired First Out)
    expiry_date: Optional[date] = Field(default=None, index=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    inventory_levels: List["InventoryLevel"] = Relationship(back_populates="lot")


class InventoryLevel(SQLModel, table=True):
    """
    Current inventory level at a specific location.
    
    Tracks available quantity by location and lot, with configurable
    alert thresholds for low stock monitoring.
    
    Features:
    - Quantity tracking by location and lot
    - Configurable reorder point threshold
    - Safety stock level for critical alerts
    - Maximum stock level for overstock alerts
    - Alert trigger timestamp tracking
    """
    __tablename__ = "inventory_levels"
    __table_args__ = (
        # Composite: item + location — primary stock lookup query pattern
        Index("idx_inventory_item_location", "item_id", "location_id"),
        # Composite: location + lot — FIFO/FEFO picking queries
        Index("idx_inventory_location_lot", "location_id", "lot_id"),
        # Partial: only records where an alert has been triggered (dashboard)
        Index("idx_inventory_low_stock", "item_id", "location_id",
              postgresql_where=text("alert_triggered_at IS NOT NULL")),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    location_id: int = Field(foreign_key="inventory_location.id", index=True)
    item_id: int = Field(foreign_key="items.item_id", index=True)
    lot_id: Optional[int] = Field(default=None, foreign_key="stock_lots.id", index=True)
    
    quantity_available: int = Field(default=0)
    reserved_quantity: int = Field(
        default=0,
        description="Stock allocated to open orders — not yet shipped",
    )

    # Alert thresholds
    reorder_point: Optional[int] = Field(
        default=None,
        description="Quantity threshold to trigger reorder alert"
    )
    safety_stock: Optional[int] = Field(
        default=None,
        description="Minimum safety stock level (critical threshold)"
    )
    max_stock: Optional[int] = Field(
        default=None,
        description="Maximum stock level (overstock threshold)"
    )
    
    # Alert status tracking
    alert_triggered_at: Optional[datetime] = Field(
        default=None,
        index=True,
        description="Timestamp when low stock alert was last triggered"
    )
    alert_acknowledged: bool = Field(
        default=False,
        description="Whether the current alert has been acknowledged"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    location: Optional[InventoryLocation] = Relationship(back_populates="inventory_levels")
    lot: Optional[StockLot] = Relationship(back_populates="inventory_levels")
    replenishment_history: List["InventoryReplenishmentHistory"] = Relationship(
        back_populates="inventory_level"
    )
    alerts: List["InventoryAlert"] = Relationship(back_populates="inventory_level")
    
    @property
    def atp(self) -> int:
        """Available-to-promise: on-hand minus reserved."""
        return max(0, self.quantity_available - self.reserved_quantity)

    @property
    def stock_status(self) -> str:
        """Determine current stock status based on ATP (available-to-promise)."""
        qty = self.atp
        if qty == 0:
            return "OUT_OF_STOCK"
        if self.safety_stock and qty <= self.safety_stock:
            return "CRITICAL"
        if self.reorder_point and qty <= self.reorder_point:
            return "LOW"
        if self.max_stock and qty >= self.max_stock:
            return "OVERSTOCK"
        return "OK"


class InventoryReplenishmentHistory(SQLModel, table=True):
    """
    Tracks changes to replenishment triggers.
    
    Records when replenishment thresholds are modified,
    whether by user or automated bot.
    """
    __tablename__ = "inventory_replenishment_history"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    inventory_level_id: int = Field(foreign_key="inventory_levels.id", index=True)
    
    # Trigger values
    previous_trigger: Optional[int] = Field(default=None)
    new_trigger: Optional[int] = Field(default=None)
    
    # Who made the change
    changed_by_user_id: Optional[int] = Field(
        default=None, 
        foreign_key="users.user_id"
    )
    bot_intervene: bool = Field(
        default=False,
        description="True if change was made by automated system"
    )
    
    changed_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    inventory_level: Optional[InventoryLevel] = Relationship(
        back_populates="replenishment_history"
    )


# =============================================================================
# Inventory Alert Table
# =============================================================================

class InventoryAlert(SQLModel, table=True):
    """
    Inventory alert tracking for low stock and other threshold breaches.
    
    Features:
    - Tracks alert type (low_stock, out_of_stock, overstock)
    - Records quantity at time of alert
    - Supports alert resolution tracking
    - Links to inventory level, item, and warehouse
    
    Alert types:
    - low_stock: Quantity dropped below reorder_point
    - out_of_stock: Quantity reached zero
    - critical: Quantity dropped below safety_stock
    - overstock: Quantity exceeded max_stock
    """
    __tablename__ = "inventory_alerts"
    __table_args__ = (
        # Composite: resolved + type — dashboard "active alerts by type" query
        Index("idx_inventory_alerts_status_type", "is_resolved", "alert_type"),
        # Composite: warehouse + resolved — per-warehouse alert dashboard
        Index("idx_inventory_alerts_warehouse", "warehouse_id", "is_resolved"),
        # Partial: unresolved only — the hot path for the alert dashboard
        Index("idx_alerts_unresolved", "warehouse_id", "alert_type", "created_at",
              postgresql_where=text("is_resolved = FALSE")),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # References
    inventory_level_id: int = Field(foreign_key="inventory_levels.id", index=True)
    item_id: int = Field(foreign_key="items.item_id", index=True)
    warehouse_id: int = Field(foreign_key="warehouse.id", index=True)
    
    # Alert details
    alert_type: str = Field(
        max_length=50,
        index=True,
        description="Type: 'low_stock', 'out_of_stock', 'critical', 'overstock'"
    )
    current_quantity: int = Field(description="Quantity at time of alert")
    threshold_quantity: int = Field(description="Threshold that was breached")
    
    # Alert message for display
    alert_message: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Human-readable alert message"
    )
    
    # Resolution tracking
    is_resolved: bool = Field(default=False, index=True)
    resolved_at: Optional[datetime] = Field(default=None)
    resolved_by_user_id: Optional[int] = Field(
        default=None,
        foreign_key="users.user_id"
    )
    resolution_notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Notes about how the alert was resolved"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    inventory_level: Optional[InventoryLevel] = Relationship(back_populates="alerts")
    warehouse: Optional[Warehouse] = Relationship(back_populates="inventory_alerts")


# =============================================================================
# Seller-Warehouse Relationship Table
# =============================================================================

class SellerWarehouse(SQLModel, table=True):
    """
    Seller-to-warehouse fulfillment routing.
    
    Defines which warehouses a seller can fulfill orders from,
    enabling multi-warehouse fulfillment strategies.
    
    Features:
    - Many-to-many relationship between sellers and warehouses
    - Primary warehouse designation for default routing
    - Priority ordering for fulfillment preference
    - Active/inactive status for temporary routing changes
    """
    __tablename__ = "seller_warehouses"
    __table_args__ = (
        # Composite: seller + active flag — warehouse routing lookup
        Index("idx_seller_warehouses_active", "seller_id", "is_active"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # References
    seller_id: int = Field(foreign_key="seller.seller_id", index=True)
    warehouse_id: int = Field(foreign_key="warehouse.id", index=True)
    
    # Fulfillment configuration
    is_primary: bool = Field(
        default=False,
        description="Primary fulfillment warehouse for this seller"
    )
    priority: int = Field(
        default=0,
        description="Priority order for warehouse selection (lower = higher priority)"
    )
    
    # Status
    is_active: bool = Field(default=True, index=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    seller: Optional["Seller"] = Relationship(back_populates="seller_warehouses")
    warehouse: Optional[Warehouse] = Relationship(back_populates="seller_warehouses")


# Forward references for relationships defined in other modules
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.delivery import Lorry, Driver
    from app.models.orders import Order, Seller