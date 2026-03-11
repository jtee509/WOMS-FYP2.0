"""
WOMS Items Module Models

This module contains all item-related models:
- Item: Main product/item entity with variations support
- Status: Item status lookup (kept for reference, no longer FK'd from Item)
- ItemType: Item type classification
- Category: Product categories
- Brand: Brand/manufacturer information
- BaseUOM: Unit of Measure definitions
- ItemsHistory: Version control snapshot for item changes (JSONB)
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Index, Text, JSON, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB

if TYPE_CHECKING:
    from app.models.orders import OrderDetail


# =============================================================================
# Lookup Tables
# =============================================================================

class Status(SQLModel, table=True):
    """
    Item status lookup table.
    
    Examples: Active, Inactive, Discontinued, Out of Stock, etc.
    """
    __tablename__ = "status"
    
    status_id: Optional[int] = Field(default=None, primary_key=True)
    status_name: str = Field(max_length=100, unique=True, index=True)
    


class ItemType(SQLModel, table=True):
    """
    Item type classification.

    Examples: Raw Material, Finished Good, Component, Packaging, etc.
    """
    __tablename__ = "item_type"
    __table_args__ = (
        Index("idx_item_type_not_deleted", "item_type_id", postgresql_where=text("deleted_at IS NULL")),
    )

    item_type_id: Optional[int] = Field(default=None, primary_key=True)
    item_type_name: str = Field(max_length=100, unique=True, index=True)
    deleted_at: Optional[datetime] = Field(default=None)

    # Relationships
    items: List["Item"] = Relationship(back_populates="item_type")


class Category(SQLModel, table=True):
    """
    Product category classification.

    Examples: Electronics, Clothing, Food & Beverage, etc.
    """
    __tablename__ = "category"
    __table_args__ = (
        Index("idx_category_not_deleted", "category_id", postgresql_where=text("deleted_at IS NULL")),
    )

    category_id: Optional[int] = Field(default=None, primary_key=True)
    category_name: str = Field(max_length=100, unique=True, index=True)
    deleted_at: Optional[datetime] = Field(default=None)

    # Relationships
    items: List["Item"] = Relationship(back_populates="category")


class Brand(SQLModel, table=True):
    """
    Brand/manufacturer information.
    """
    __tablename__ = "brand"
    __table_args__ = (
        Index("idx_brand_not_deleted", "brand_id", postgresql_where=text("deleted_at IS NULL")),
    )

    brand_id: Optional[int] = Field(default=None, primary_key=True)
    brand_name: str = Field(max_length=200, unique=True, index=True)
    deleted_at: Optional[datetime] = Field(default=None)

    # Relationships
    items: List["Item"] = Relationship(back_populates="brand")


class BaseUOM(SQLModel, table=True):
    """
    Base Unit of Measure definitions.

    Examples: Each, Box, Carton, Kg, Liter, etc.
    """
    __tablename__ = "base_uom"
    __table_args__ = (
        Index("idx_base_uom_not_deleted", "uom_id", postgresql_where=text("deleted_at IS NULL")),
    )

    uom_id: Optional[int] = Field(default=None, primary_key=True)
    uom_name: str = Field(max_length=50, unique=True, index=True)
    deleted_at: Optional[datetime] = Field(default=None)

    # Relationships
    items: List["Item"] = Relationship(back_populates="uom")


# =============================================================================
# Main Item Table
# =============================================================================

class Item(SQLModel, table=True):
    """
    Main item/product entity.
    
    Features:
    - Hierarchical structure via parent_id (for variations)
    - JSONB variations data for flexible attribute storage
    - Soft delete support via deleted_at/deleted_by
    - Full relationship mapping to lookup tables
    """
    __tablename__ = "items"
    __table_args__ = (
        # GIN index on JSONB variations_data — enables @> containment queries
        Index("idx_items_variations_gin", "variations_data",
              postgresql_using="gin",
              postgresql_ops={"variations_data": "jsonb_path_ops"}),
        # Partial index: only active (non-deleted) items — most common filter
        Index("idx_items_active", "item_id", "master_sku",
              postgresql_where=text("deleted_at IS NULL")),
    )

    # Primary Key
    item_id: Optional[int] = Field(default=None, primary_key=True)
    
    # Self-referencing for variations/parent items
    parent_id: Optional[int] = Field(
        default=None, 
        foreign_key="items.item_id",
        index=True,
        description="Parent item ID for variations"
    )
    
    # Core Fields
    item_name: str = Field(max_length=500, index=True)
    master_sku: str = Field(max_length=100, unique=True, index=True)
    sku_name: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    image_url: Optional[str] = Field(default=None, max_length=500, description="URL/path to main product image")

    # Foreign Keys to Lookups
    uom_id: Optional[int] = Field(default=None, foreign_key="base_uom.uom_id")
    brand_id: Optional[int] = Field(default=None, foreign_key="brand.brand_id")
    item_type_id: Optional[int] = Field(default=None, foreign_key="item_type.item_type_id")
    category_id: Optional[int] = Field(default=None, foreign_key="category.category_id")

    # Active flag (replaces old status_id FK)
    is_active: bool = Field(default=True, index=True)
    
    # Variation Support
    has_variation: bool = Field(default=False)
    
    # JSONB field for flexible variation attributes
    # Stores: {"variation_id": 1, "variation_type": "Color", "variation_name": "Red"}
    variations_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="JSONB field for variation attributes"
    )
    
    # Soft Delete Fields
    deleted_at: Optional[datetime] = Field(default=None, index=True)
    deleted_by: Optional[int] = Field(
        default=None, 
        foreign_key="users.user_id",
        description="User who deleted this item"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    uom: Optional[BaseUOM] = Relationship(back_populates="items")
    brand: Optional[Brand] = Relationship(back_populates="items")
    item_type: Optional[ItemType] = Relationship(back_populates="items")
    category: Optional[Category] = Relationship(back_populates="items")
    
    # Self-referencing relationships
    parent: Optional["Item"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Item.item_id"}
    )
    children: List["Item"] = Relationship(back_populates="parent")
    
    # History tracking
    history_records: List["ItemsHistory"] = Relationship(back_populates="item")
    
    # Order details that reference this item
    order_details: List["OrderDetail"] = Relationship(back_populates="resolved_item")
    
    @property
    def is_deleted(self) -> bool:
        """Check if item is soft-deleted."""
        return self.deleted_at is not None


# =============================================================================
# Version Control Snapshot (Items History)
# =============================================================================

class ItemsHistory(SQLModel, table=True):
    """
    Version Control Snapshot for Items.
    
    Tracks all changes to items using JSONB to store only modified fields.
    This implements the audit trail / version control pattern.
    
    Features:
    - JSONB snapshot_data stores only changed fields
    - Tracks operation type (INSERT, UPDATE, DELETE)
    - Links to user who made the change
    - Reference to the original item
    
    Example snapshot_data for an UPDATE:
    {
        "sku": "NEW-SKU-123",
        "brand_id": 2,
        "category_id": 5,
        "previous_values": {
            "sku": "OLD-SKU-123",
            "brand_id": 1,
            "category_id": 3
        }
    }
    """
    __tablename__ = "items_history"
    __table_args__ = (
        # GIN index on snapshot_data JSONB — enables field-level audit queries
        Index("idx_items_history_snapshot_gin", "snapshot_data",
              postgresql_using="gin",
              postgresql_ops={"snapshot_data": "jsonb_path_ops"}),
    )

    # Primary Key
    history_id: Optional[int] = Field(default=None, primary_key=True)
    
    # Reference to the item
    reference_id: int = Field(foreign_key="items.item_id", index=True)
    
    # Change tracking
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    changed_by_user_id: Optional[int] = Field(
        default=None, 
        foreign_key="users.user_id",
        index=True
    )
    
    # Operation type: INSERT, UPDATE, DELETE
    operation: str = Field(max_length=20, index=True)
    
    # JSONB snapshot - stores only changed fields
    # Contains: {"field_name": "new_value", "previous_values": {"field_name": "old_value"}}
    snapshot_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
        description="JSONB snapshot of changed fields"
    )
    
    # Relationships
    item: Optional[Item] = Relationship(back_populates="history_records")

